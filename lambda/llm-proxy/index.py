import json
import os
import boto3
import logging
from typing import Dict, Any, Optional

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Bedrockクライアントの初期化
bedrock_runtime = boto3.client('bedrock-runtime')

# 環境変数
ENV_NAME = os.environ.get('ENV_NAME', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'masjp')

# デフォルトのモデルID
DEFAULT_MODEL_ID = 'anthropic.claude-3-5-sonnet-20241022-v2:0'

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    LLMプロキシLambda関数のハンドラー
    
    Args:
        event: Lambda関数のイベントデータ
        context: Lambda関数のコンテキスト
        
    Returns:
        LLMからのレスポンス
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # イベントからパラメータを取得
        model_id = event.get('model_id', DEFAULT_MODEL_ID)
        messages = event.get('messages', [])
        prompt = event.get('prompt')  # 単一のプロンプトもサポート
        temperature = event.get('temperature', 0.7)
        max_tokens = event.get('max_tokens', 4096)
        stream = event.get('stream', False)
        
        # プロンプトがある場合はメッセージに変換
        if prompt and not messages:
            messages = [{"role": "user", "content": prompt}]
        
        # メッセージの検証
        if not messages:
            return {
                'error': 'No messages provided',
                'status': 'failed'
            }
        
        logger.info(f"Processing messages: {json.dumps(messages)}")
        
        # メッセージの形式を確認し、必要に応じて修正
        valid_messages = []
        for msg in messages:
            if msg.get('role') in ['user', 'assistant']:
                valid_messages.append(msg)
            elif msg.get('role') == 'system':
                # システムプロンプトをユーザーメッセージの前に追加
                valid_messages.append({
                    'role': 'user',
                    'content': f"Instructions: {msg.get('content')}\n\nPlease follow these instructions for all your responses."
                })
        
        # 有効なメッセージがない場合、エラー
        if not valid_messages:
            return {
                'error': 'No valid messages after processing',
                'status': 'failed'
            }
        
        # リクエストボディの作成
        request_body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': valid_messages,
            'temperature': temperature
        }
        
        # Bedrockを呼び出し
        # if stream:
        #     response = bedrock_runtime.invoke_model_with_response_stream(
        #         modelId=model_id,
        #         body=json.dumps(request_body)
        #     )
        #     # ストリーミングレスポンスの処理は複雑なので、ここでは簡略化
        #     return {
        #         'message': 'Streaming not fully implemented in this example',
        #         'status': 'success'
        #     }
        # else:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # レスポンスの解析
        response_body = json.loads(response.get('body').read())
        
        # 統一された形式に変換
        # Anthropic Claude形式のレスポンスを処理
        if 'content' in response_body:
            # 複数のコンテンツブロックがある場合は連結
            if isinstance(response_body['content'], list):
                content_text = ""
                for content_block in response_body['content']:
                    if content_block.get('type') == 'text':
                        content_text += content_block.get('text', '')
                return {
                    'content': content_text,
                    'status': 'success'
                }
            else:
                return {
                    'content': response_body['content'],
                    'status': 'success'
                }
        else:
            logger.warning(f"Unexpected response format: {json.dumps(response_body)}")
            return {
                'content': str(response_body),
                'status': 'success'
            }
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'error': str(e),
            'status': 'failed'
        }