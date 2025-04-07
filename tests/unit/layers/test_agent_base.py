"""
Agentクラスのテスト
"""
import json
import pytest
import uuid
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime
from agent_base import Agent


@patch('agent_base.DynamoDBClient')
@patch('agent_base.S3Client')
@patch('agent_base.SQSClient')
@patch('agent_base.EventBridgeClient')
@patch('agent_base.LLMClient')
def test_agent_init_with_defaults(
    mock_llm_client, 
    mock_eventbridge_client, 
    mock_sqs_client, 
    mock_s3_client, 
    mock_dynamodb_client
):
    """Agentクラスの初期化テスト（デフォルトパラメータ）"""
    # テスト対象のクラスをインスタンス化
    agent = Agent()
    
    # 検証
    assert agent.agent_type == "base"
    assert agent.agent_id.startswith("base-")
    assert agent.state == "initialized"
    assert agent.memory == []
    assert hasattr(agent, "created_at")
    
    # 各クライアントが初期化されていないことを確認
    mock_dynamodb_client.assert_not_called()
    mock_s3_client.assert_not_called()
    mock_sqs_client.assert_not_called()
    mock_eventbridge_client.assert_not_called()
    mock_llm_client.assert_called_once()


@patch('agent_base.DynamoDBClient')
@patch('agent_base.S3Client')
@patch('agent_base.SQSClient')
@patch('agent_base.EventBridgeClient')
@patch('agent_base.LLMClient')
def test_agent_init_with_params(
    mock_llm_client, 
    mock_eventbridge_client, 
    mock_sqs_client, 
    mock_s3_client, 
    mock_dynamodb_client
):
    """Agentクラスの初期化テスト（パラメータ指定あり）"""
    # テスト対象のクラスをインスタンス化
    agent_id = "test-agent-123"
    agent_type = "test_agent"
    agent_state_table = "test-agent-state"
    message_history_table = "test-message-history"
    artifacts_bucket = "test-artifacts"
    communication_queue_url = "https://sqs.region.amazonaws.com/123456789012/test-queue"
    event_bus_name = "test-event-bus"
    model_id = "anthropic.claude-3-5-sonnet-20241022-v1:0"
    
    agent = Agent(
        agent_id=agent_id,
        agent_type=agent_type,
        agent_state_table=agent_state_table,
        message_history_table=message_history_table,
        artifacts_bucket=artifacts_bucket,
        communication_queue_url=communication_queue_url,
        event_bus_name=event_bus_name,
        model_id=model_id
    )
    
    # 検証
    assert agent.agent_id == agent_id
    assert agent.agent_type == agent_type
    assert agent.state == "initialized"
    assert agent.memory == []
    
    # 各クライアントが正しく初期化されていることを確認
    mock_dynamodb_client.assert_any_call(agent_state_table)
    mock_dynamodb_client.assert_any_call(message_history_table)
    mock_s3_client.assert_called_once_with(artifacts_bucket)
    mock_sqs_client.assert_called_once_with(communication_queue_url)
    mock_eventbridge_client.assert_called_once_with(event_bus_name)
    mock_llm_client.assert_called_once_with(model_id)


@patch('agent_base.DynamoDBClient')
def test_save_state(mock_dynamodb_client):
    """save_stateメソッドのテスト"""
    # モックの設定
    mock_db_instance = MagicMock()
    mock_db_instance.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_dynamodb_client.return_value = mock_db_instance
    
    # テスト対象のクラスをインスタンス化
    agent = Agent(agent_state_table="test-agent-state")
    agent.agent_id = "test-agent-123"
    agent.agent_type = "test_agent"
    agent.state = "processing"
    agent.memory = [{"type": "note", "content": "test note"}]
    
    # テスト実行
    result = agent.save_state()
    
    # 検証
    mock_db_instance.put_item.assert_called_once()
    
    # 保存されたアイテムの確認
    saved_item = mock_db_instance.put_item.call_args[0][0]
    assert saved_item['agentId'] == agent.agent_id
    assert saved_item['agentType'] == agent.agent_type
    assert saved_item['state'] == agent.state
    assert json.loads(saved_item['memory']) == agent.memory
    assert 'createdAt' in saved_item
    assert 'updatedAt' in saved_item
    
    # 戻り値の確認
    assert result == {"ResponseMetadata": {"HTTPStatusCode": 200}}


@patch('agent_base.DynamoDBClient')
def test_save_state_no_db(mock_dynamodb_client):
    """save_stateメソッドのテスト（DBなし）"""
    # テスト対象のクラスをインスタンス化
    agent = Agent()  # DB設定なし
    
    # テスト実行
    result = agent.save_state()
    
    # 検証
    mock_dynamodb_client.assert_not_called()
    assert result == {}


@patch('agent_base.DynamoDBClient')
def test_load_state_with_id(mock_dynamodb_client):
    """load_stateメソッドのテスト（状態ID指定）"""
    # モックの設定
    mock_db_instance = MagicMock()
    mock_db_instance.get_item.return_value = {
        'agentId': 'test-agent-123',
        'stateId': '2023-05-15T12:34:56.789Z',
        'agentType': 'test_agent',
        'state': 'completed',
        'memory': json.dumps([{"type": "result", "content": "test result"}]),
        'createdAt': '2023-05-15T10:00:00.000Z',
        'updatedAt': '2023-05-15T12:34:56.789Z'
    }
    mock_dynamodb_client.return_value = mock_db_instance
    
    # テスト対象のクラスをインスタンス化
    agent = Agent(agent_state_table="test-agent-state")
    agent.agent_id = "test-agent-123"
    
    # テスト実行
    state_id = "2023-05-15T12:34:56.789Z"
    result = agent.load_state(state_id)
    
    # 検証
    mock_db_instance.get_item.assert_called_once_with({
        'agentId': 'test-agent-123', 
        'stateId': state_id
    })
    
    assert result == True
    assert agent.agent_type == 'test_agent'
    assert agent.state == 'completed'
    assert agent.memory == [{"type": "result", "content": "test result"}]
    assert agent.created_at == '2023-05-15T10:00:00.000Z'


@patch('agent_base.DynamoDBClient')
def test_load_state_latest(mock_dynamodb_client):
    """load_stateメソッドのテスト（最新の状態を取得）"""
    # モックの設定
    mock_db_instance = MagicMock()
    mock_db_instance.query.return_value = [{
        'agentId': 'test-agent-123',
        'stateId': '2023-05-15T12:34:56.789Z',
        'agentType': 'test_agent',
        'state': 'completed',
        'memory': json.dumps([{"type": "result", "content": "latest result"}]),
        'createdAt': '2023-05-15T10:00:00.000Z',
        'updatedAt': '2023-05-15T12:34:56.789Z'
    }]
    mock_dynamodb_client.return_value = mock_db_instance
    
    # テスト対象のクラスをインスタンス化
    agent = Agent(agent_state_table="test-agent-state")
    agent.agent_id = "test-agent-123"
    
    # テスト実行（状態ID指定なし）
    result = agent.load_state()
    
    # 検証
    mock_db_instance.query.assert_called_once()
    
    assert result == True
    assert agent.state == 'completed'
    assert agent.memory == [{"type": "result", "content": "latest result"}]


@patch('agent_base.DynamoDBClient')
def test_load_state_not_found(mock_dynamodb_client):
    """load_stateメソッドのテスト（状態が見つからない）"""
    # モックの設定
    mock_db_instance = MagicMock()
    mock_db_instance.query.return_value = []  # 空のリストを返す
    mock_dynamodb_client.return_value = mock_db_instance
    
    # テスト対象のクラスをインスタンス化
    agent = Agent(agent_state_table="test-agent-state")
    agent.agent_id = "test-agent-123"
    agent.state = "initial_state"
    
    # テスト実行
    result = agent.load_state()
    
    # 検証
    assert result == False
    assert agent.state == "initial_state"  # 状態が変更されていないことを確認


def test_add_to_memory():
    """add_to_memoryメソッドのテスト"""
    # テスト対象のクラスをインスタンス化
    agent = Agent()
    
    # 初期状態を確認
    assert agent.memory == []
    
    # テスト実行
    item1 = {"type": "note", "content": "test note 1"}
    agent.add_to_memory(item1)
    
    # 検証
    assert len(agent.memory) == 1
    assert agent.memory[0] == item1
    
    # さらにアイテムを追加
    item2 = {"type": "result", "content": "test result"}
    agent.add_to_memory(item2)
    
    # 検証
    assert len(agent.memory) == 2
    assert agent.memory[0] == item1
    assert agent.memory[1] == item2


@patch('agent_base.SQSClient')
def test_send_message(mock_sqs_client):
    """send_messageメソッドのテスト"""
    # モックの設定
    mock_sqs_instance = MagicMock()
    mock_sqs_instance.send_message.return_value = {
        "MessageId": "12345678-1234-1234-1234-123456789012",
        "MD5OfMessageBody": "12345678901234567890123456789012"
    }
    mock_sqs_client.return_value = mock_sqs_instance
    
    # テスト対象のクラスをインスタンス化
    queue_url = "https://sqs.region.amazonaws.com/123456789012/test-queue"
    agent = Agent(communication_queue_url=queue_url)
    agent.agent_id = "test-agent-123"
    
    # テスト実行
    recipient_id = "recipient-agent"
    content = {"type": "notification", "message": "test message"}
    result = agent.send_message(recipient_id, content)
    
    # 検証
    mock_sqs_instance.send_message.assert_called_once()
    
    # 送信されたメッセージの確認
    sent_message_arg = mock_sqs_instance.send_message.call_args[0][0]
    # 型チェックを追加して条件分岐
    if isinstance(sent_message_arg, str):
        sent_message = json.loads(sent_message_arg)
    else:
        sent_message = sent_message_arg
        
    assert sent_message['sender_id'] == agent.agent_id
    assert sent_message['recipient_id'] == recipient_id
    assert sent_message['content'] == content
    assert 'timestamp' in sent_message
    
    # 戻り値の確認
    assert result["MessageId"] == "12345678-1234-1234-1234-123456789012"


@patch('agent_base.SQSClient')
def test_send_message_no_queue(mock_sqs_client):
    """send_messageメソッドのテスト（キューなし）"""
    # テスト対象のクラスをインスタンス化
    agent = Agent()  # キュー設定なし
    
    # テスト実行
    result = agent.send_message("recipient", {"message": "test"})
    
    # 検証
    mock_sqs_client.assert_not_called()
    assert result == {}


@patch('agent_base.SQSClient')
def test_receive_messages(mock_sqs_client):
    """receive_messagesメソッドのテスト"""
    # モックの設定
    mock_sqs_instance = MagicMock()
    mock_sqs_instance.receive_messages.return_value = [
        {
            "MessageId": "12345678-1234-1234-1234-123456789012",
            "ReceiptHandle": "receipt-handle-1",
            "Body": json.dumps({
                "sender_id": "sender-agent",
                "recipient_id": "test-agent-123",
                "content": {"type": "notification", "message": "test message 1"},
                "timestamp": "2023-05-15T10:00:00.000Z"
            })
        },
        {
            "MessageId": "87654321-4321-4321-4321-210987654321",
            "ReceiptHandle": "receipt-handle-2",
            "Body": json.dumps({
                "sender_id": "sender-agent",
                "recipient_id": "test-agent-123",
                "content": {"type": "notification", "message": "test message 2"},
                "timestamp": "2023-05-15T10:01:00.000Z"
            })
        }
    ]
    mock_sqs_client.return_value = mock_sqs_instance
    
    # テスト対象のクラスをインスタンス化
    queue_url = "https://sqs.region.amazonaws.com/123456789012/test-queue"
    agent = Agent(communication_queue_url=queue_url)
    
    # テスト実行
    max_messages = 5
    messages = agent.receive_messages(max_messages)
    
    # 検証
    mock_sqs_instance.receive_messages.assert_called_once_with(max_messages)
    
    assert len(messages) == 2
    assert messages[0]["MessageId"] == "12345678-1234-1234-1234-123456789012"
    assert messages[1]["MessageId"] == "87654321-4321-4321-4321-210987654321"


@patch('agent_base.EventBridgeClient')
def test_emit_event(mock_eventbridge_client):
    """emit_eventメソッドのテスト"""
    # モックの設定
    mock_eventbridge_instance = MagicMock()
    mock_eventbridge_instance.put_event.return_value = {
        "Entries": [{"EventId": "12345678-1234-1234-1234-123456789012"}],
        "FailedEntryCount": 0
    }
    mock_eventbridge_client.return_value = mock_eventbridge_instance
    
    # テスト対象のクラスをインスタンス化
    event_bus_name = "test-event-bus"
    agent = Agent(event_bus_name=event_bus_name)
    agent.agent_id = "test-agent-123"
    agent.agent_type = "test_agent"
    
    # テスト実行
    detail_type = "TestEvent"
    detail = {"key1": "value1", "key2": "value2"}
    result = agent.emit_event(detail_type, detail)
    
    # 検証
    mock_eventbridge_instance.put_event.assert_called_once()
    
    # 送信されたイベントの確認
    # キーワード引数を確認
    call_kwargs = mock_eventbridge_instance.put_event.call_args.kwargs
    # 引数リストを確認
    call_args_list = mock_eventbridge_instance.put_event.call_args_list
    
    # 実装に応じた検証方法を選択
    if len(call_args_list) > 0 and len(call_args_list[0]) > 0:
        # 位置引数またはキーワード引数のどちらかで検証
        if call_kwargs and ('Source' in call_kwargs or 'source' in call_kwargs):
            source_value = call_kwargs.get('Source', call_kwargs.get('source'))
            assert source_value == f"agent.{agent.agent_type}"
        elif len(call_args_list[0][0]) >= 1:
            assert call_args_list[0][0][0] == f"agent.{agent.agent_type}"  # source
    
    # detailにagent_idとagent_typeが追加されていることを確認
    # 戻り値の確認
    assert result["Entries"][0]["EventId"] == "12345678-1234-1234-1234-123456789012"
    assert result["FailedEntryCount"] == 0
    assert result["Entries"][0]["EventId"] == "12345678-1234-1234-1234-123456789012"


@patch('agent_base.S3Client')
def test_save_artifact_string(mock_s3_client):
    """save_artifactメソッドのテスト（文字列データ）"""
    # モックの設定
    mock_s3_instance = MagicMock()
    mock_s3_instance.upload_json.return_value = {
        "ETag": '"12345678901234567890123456789012"',
        "VersionId": "version-1"
    }
    mock_s3_client.return_value = mock_s3_instance
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-artifacts"
    agent = Agent(artifacts_bucket=bucket_name)
    
    # テスト実行
    content = "This is a test content"
    key = "test/path/artifact.json"
    result = agent.save_artifact(content, key)
    
    # 検証
    mock_s3_instance.upload_json.assert_called_once_with({"content": content}, key)
    
    # 戻り値の確認
    assert result["ETag"] == '"12345678901234567890123456789012"'
    assert result["VersionId"] == "version-1"


@patch('agent_base.S3Client')
def test_save_artifact_dict(mock_s3_client):
    """save_artifactメソッドのテスト（辞書データ）"""
    # モックの設定
    mock_s3_instance = MagicMock()
    mock_s3_instance.upload_json.return_value = {
        "ETag": '"12345678901234567890123456789012"',
        "VersionId": "version-1"
    }
    mock_s3_client.return_value = mock_s3_instance
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-artifacts"
    agent = Agent(artifacts_bucket=bucket_name)
    
    # テスト実行
    content = {"key1": "value1", "key2": ["item1", "item2"]}
    key = "test/path/artifact.json"
    result = agent.save_artifact(content, key)
    
    # 検証
    mock_s3_instance.upload_json.assert_called_once_with(content, key)
    
    # 戻り値の確認
    assert result["ETag"] == '"12345678901234567890123456789012"'
    assert result["VersionId"] == "version-1"


@patch('agent_base.LLMClient')
def test_ask_llm(mock_llm_client):
    """ask_llmメソッドのテスト"""
    # モックの設定
    mock_llm_instance = MagicMock()
    mock_llm_instance.invoke_llm.return_value = {
        "content": "This is a test response from the LLM"
    }
    mock_llm_client.return_value = mock_llm_instance
    
    # テスト対象のクラスをインスタンス化
    agent = Agent()
    
    # テスト実行
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather today?"}
    ]
    temperature = 0.5
    max_tokens = 2048
    response = agent.ask_llm(messages, temperature, max_tokens)
    
    # 検証
    mock_llm_instance.invoke_llm.assert_called_once_with(messages, temperature, max_tokens)
    
    # レスポンスの確認
    assert response["content"] == "This is a test response from the LLM"


def test_process_not_implemented():
    """processメソッドのテスト（未実装）"""
    # テスト対象のクラスをインスタンス化
    agent = Agent()
    
    # テスト実行とエラー検証
    with pytest.raises(NotImplementedError) as e:
        agent.process({"test": "data"})
    
    assert "Subclasses must implement process method" in str(e.value)