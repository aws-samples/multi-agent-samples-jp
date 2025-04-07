"""
SQSClientとEventBridgeClientのテスト
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from agent_utils import SQSClient, EventBridgeClient


@patch('agent_utils.boto3.client')
def test_sqs_client_init(mock_boto3_client):
    """SQSClientの初期化テスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    queue_url = "https://sqs.ap-northeast-1.amazonaws.com/123456789012/test-queue"
    client = SQSClient(queue_url)
    
    # 検証
    assert client.sqs == mock_client
    assert client.queue_url == queue_url
    mock_boto3_client.assert_called_once_with('sqs')


@patch('agent_utils.boto3.client')
def test_send_message(mock_boto3_client):
    """send_messageメソッドのテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.send_message.return_value = {
        "MessageId": "12345678-1234-1234-1234-123456789012",
        "MD5OfMessageBody": "12345678901234567890123456789012",
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    queue_url = "https://sqs.ap-northeast-1.amazonaws.com/123456789012/test-queue"
    client = SQSClient(queue_url)
    
    # テスト実行
    message = {"id": "1", "content": "test message"}
    response = client.send_message(message)
    
    # 検証
    mock_client.send_message.assert_called_once_with(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )
    assert response["MessageId"] == "12345678-1234-1234-1234-123456789012"


@patch('agent_utils.boto3.client')
def test_receive_messages(mock_boto3_client):
    """receive_messagesメソッドのテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.receive_message.return_value = {
        "Messages": [
            {
                "MessageId": "12345678-1234-1234-1234-123456789012",
                "ReceiptHandle": "receipt-handle-1",
                "Body": json.dumps({"id": "1", "content": "test message 1"})
            },
            {
                "MessageId": "87654321-4321-4321-4321-210987654321",
                "ReceiptHandle": "receipt-handle-2",
                "Body": json.dumps({"id": "2", "content": "test message 2"})
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    queue_url = "https://sqs.ap-northeast-1.amazonaws.com/123456789012/test-queue"
    client = SQSClient(queue_url)
    
    # テスト実行
    messages = client.receive_messages(max_messages=5)
    
    # 検証
    mock_client.receive_message.assert_called_once_with(
        QueueUrl=queue_url,
        MaxNumberOfMessages=5,
        WaitTimeSeconds=20
    )
    assert len(messages) == 2
    assert messages[0]["MessageId"] == "12345678-1234-1234-1234-123456789012"
    assert messages[1]["MessageId"] == "87654321-4321-4321-4321-210987654321"


@patch('agent_utils.boto3.client')
def test_receive_messages_empty(mock_boto3_client):
    """receive_messagesメソッドのテスト（メッセージがない場合）"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.receive_message.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    queue_url = "https://sqs.ap-northeast-1.amazonaws.com/123456789012/test-queue"
    client = SQSClient(queue_url)
    
    # テスト実行
    messages = client.receive_messages()
    
    # 検証
    mock_client.receive_message.assert_called_once_with(
        QueueUrl=queue_url,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20
    )
    assert len(messages) == 0


@patch('agent_utils.boto3.client')
def test_delete_message(mock_boto3_client):
    """delete_messageメソッドのテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.delete_message.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    queue_url = "https://sqs.ap-northeast-1.amazonaws.com/123456789012/test-queue"
    client = SQSClient(queue_url)
    
    # テスト実行
    receipt_handle = "receipt-handle-1"
    response = client.delete_message(receipt_handle)
    
    # 検証
    mock_client.delete_message.assert_called_once_with(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@patch('agent_utils.boto3.client')
def test_eventbridge_client_init(mock_boto3_client):
    """EventBridgeClientの初期化テスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    event_bus_name = "test-event-bus"
    client = EventBridgeClient(event_bus_name)
    
    # 検証
    assert client.events == mock_client
    assert client.event_bus_name == event_bus_name
    mock_boto3_client.assert_called_once_with('events')


@patch('agent_utils.boto3.client')
def test_put_event(mock_boto3_client):
    """put_eventメソッドのテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [
            {
                "EventId": "12345678-1234-1234-1234-123456789012"
            }
        ],
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    event_bus_name = "test-event-bus"
    client = EventBridgeClient(event_bus_name)
    
    # テスト実行
    source = "agent.product_manager"
    detail_type = "RequirementAnalysisCompleted"
    detail = {
        "project_id": "proj123",
        "analysis_id": "abc123",
        "requirement": "テスト要件"
    }
    response = client.put_event(source, detail_type, detail)
    
    # 検証
    mock_client.put_events.assert_called_once_with(
        Entries=[
            {
                'Source': source,
                'DetailType': detail_type,
                'Detail': json.dumps(detail),
                'EventBusName': event_bus_name
            }
        ]
    )
    assert response["FailedEntryCount"] == 0
    assert "EventId" in response["Entries"][0]