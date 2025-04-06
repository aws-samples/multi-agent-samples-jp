"""
LLMClientのテスト
"""
import json
import pytest
import os
from unittest.mock import MagicMock, patch, ANY
from io import BytesIO
from llm_client import LLMClient


@patch('llm_client.boto3.client')
def test_llm_client_init_default_model(mock_boto3_client):
    """LLMClientの初期化テスト（デフォルトモデル）"""
    # モックの設定
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    client = LLMClient()
    
    # 検証
    assert client.bedrock_runtime == mock_client
    assert client.model_id == 'anthropic.claude-3-sonnet-20240229-v1:0'  # デフォルト値
    mock_boto3_client.assert_called_once_with('bedrock-runtime', config=ANY)


@patch('llm_client.boto3.client')
def test_llm_client_init_custom_model(mock_boto3_client):
    """LLMClientの初期化テスト（カスタムモデル）"""
    # モックの設定
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    custom_model_id = 'anthropic.claude-3-5-sonnet-20241022-v1:0'
    client = LLMClient(model_id=custom_model_id)
    
    # 検証
    assert client.bedrock_runtime == mock_client
    assert client.model_id == custom_model_id
    mock_boto3_client.assert_called_once_with('bedrock-runtime', config=ANY)


@patch('llm_client.boto3.client')
def test_llm_client_init_from_env(mock_boto3_client):
    """LLMClientの初期化テスト（環境変数からモデル設定）"""
    # モックの設定
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # 環境変数を設定
    with patch.dict(os.environ, {'DEFAULT_MODEL_ID': 'anthropic.claude-3-5-sonnet-20241022-v1:0'}):
        # テスト対象のクラスをインスタンス化
        client = LLMClient()
    
    # 検証
    assert client.bedrock_runtime == mock_client
    assert client.model_id == 'anthropic.claude-3-5-sonnet-20241022-v1:0'
    mock_boto3_client.assert_called_once_with('bedrock-runtime', config=ANY)


@patch('llm_client.boto3.client')
def test_invoke_llm_simple_message(mock_boto3_client):
    """invoke_llmメソッドのテスト（シンプルなメッセージ）"""
    # モックの設定
    mock_response = {
        'body': BytesIO(json.dumps({
            'content': [
                {
                    'type': 'text',
                    'text': 'This is a test response'
                }
            ]
        }).encode('utf-8'))
    }
    
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_response
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    client = LLMClient()
    
    # テスト実行
    messages = [
        {"role": "user", "content": "What is the weather today?"}
    ]
    response = client.invoke_llm(messages)
    
    # 検証
    mock_client.invoke_model.assert_called_once_with(
        modelId=client.model_id,
        body=ANY  # 複雑な内容なのでANYで検証
    )
    
    # 呼び出し時の引数の詳細を取得して検証
    actual_body = json.loads(mock_client.invoke_model.call_args[1]['body'])
    assert actual_body['max_tokens'] == 4096
    assert actual_body['temperature'] == 0.7
    assert len(actual_body['messages']) == 1
    assert actual_body['messages'][0]['role'] == 'user'
    assert actual_body['messages'][0]['content'] == 'What is the weather today?'
    
    # レスポンスの検証
    assert response['content'] == 'This is a test response'


@patch('llm_client.boto3.client')
def test_invoke_llm_with_system_message(mock_boto3_client):
    """invoke_llmメソッドのテスト（システムメッセージあり）"""
    # モックの設定
    mock_response = {
        'body': BytesIO(json.dumps({
            'content': [
                {
                    'type': 'text',
                    'text': 'The weather is sunny today'
                }
            ]
        }).encode('utf-8'))
    }
    
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_response
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    client = LLMClient()
    
    # テスト実行
    messages = [
        {"role": "system", "content": "You are a helpful weather assistant."},
        {"role": "user", "content": "What is the weather today?"}
    ]
    response = client.invoke_llm(messages)
    
    # 検証
    mock_client.invoke_model.assert_called_once_with(
        modelId=client.model_id,
        body=ANY
    )
    
    # 呼び出し時の引数の詳細を取得して検証
    actual_body = json.loads(mock_client.invoke_model.call_args[1]['body'])
    assert len(actual_body['messages']) == 1
    assert actual_body['messages'][0]['role'] == 'user'
    
    # システムメッセージの処理方法を確認
    # 方法1: システムメッセージがユーザーメッセージに含まれていない場合、
    # anthropic_versionパラメータが設定されているか確認
    assert "anthropic_version" in actual_body
    assert actual_body["anthropic_version"] == "bedrock-2023-05-31"
    
    # 方法2: ユーザーメッセージの内容を確認
    assert actual_body['messages'][0]['content'] == "What is the weather today?"
    
    # レスポンスの検証
    assert response['content'] == 'The weather is sunny today'


@patch('llm_client.boto3.client')
def test_invoke_llm_conversation(mock_boto3_client):
    """invoke_llmメソッドのテスト（会話形式）"""
    # モックの設定
    mock_response = {
        'body': BytesIO(json.dumps({
            'content': [
                {
                    'type': 'text',
                    'text': 'I recommend bringing an umbrella'
                }
            ]
        }).encode('utf-8'))
    }
    
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_response
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    client = LLMClient()
    
    # テスト実行
    messages = [
        {"role": "user", "content": "What is the weather today?"},
        {"role": "assistant", "content": "The weather is rainy today."},
        {"role": "user", "content": "Should I bring an umbrella?"}
    ]
    response = client.invoke_llm(messages)
    
    # 検証
    mock_client.invoke_model.assert_called_once_with(
        modelId=client.model_id,
        body=ANY
    )
    
    # 呼び出し時の引数の詳細を取得して検証
    actual_body = json.loads(mock_client.invoke_model.call_args[1]['body'])
    assert len(actual_body['messages']) == 3
    assert actual_body['messages'][0]['role'] == 'user'
    assert actual_body['messages'][1]['role'] == 'assistant'
    assert actual_body['messages'][2]['role'] == 'user'
    
    # レスポンスの検証
    assert response['content'] == 'I recommend bringing an umbrella'


@patch('llm_client.boto3.client')
def test_invoke_llm_invalid_messages(mock_boto3_client):
    """invoke_llmメソッドのテスト（無効なメッセージ）"""
    # モックの設定
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    client = LLMClient()
    
    # テスト実行 - 空のメッセージリスト
    with pytest.raises(ValueError) as e:
        client.invoke_llm([])
    
    assert "No valid messages provided" in str(e.value)
    
    # テスト実行 - システムメッセージのみ
    with pytest.raises(ValueError) as e:
        client.invoke_llm([{"role": "system", "content": "You are a helpful assistant."}])
    
    assert "No valid messages provided" in str(e.value)


@patch('llm_client.boto3.client')
def test_invoke_llm_continuous_roles(mock_boto3_client):
    """invoke_llmメソッドのテスト（連続した同じロール）"""
    # モックの設定
    mock_response = {
        'body': BytesIO(json.dumps({
            'content': [
                {
                    'type': 'text',
                    'text': 'Final response'
                }
            ]
        }).encode('utf-8'))
    }
    
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_response
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    client = LLMClient()
    
    # テスト実行 - 連続したアシスタントメッセージ
    messages = [
        {"role": "user", "content": "Initial question"},
        {"role": "assistant", "content": "First response"},
        {"role": "assistant", "content": "Second response"},
        {"role": "user", "content": "Follow-up question"}
    ]
    response = client.invoke_llm(messages)
    
    # 検証 - ダミーのユーザーメッセージが挿入されているはず
    actual_body = json.loads(mock_client.invoke_model.call_args[1]['body'])
    assert len(actual_body['messages']) == 5
    assert actual_body['messages'][0]['role'] == 'user'
    assert actual_body['messages'][1]['role'] == 'assistant'
    assert actual_body['messages'][2]['role'] == 'user'
    assert actual_body['messages'][2]['content'] == 'Please continue.'
    assert actual_body['messages'][3]['role'] == 'assistant'
    assert actual_body['messages'][4]['role'] == 'user'
    
    # レスポンスの検証
    assert response['content'] == 'Final response'