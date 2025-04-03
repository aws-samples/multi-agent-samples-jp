"""
LLMクライアントモジュール
"""
import json
import boto3
import logging
import os
from typing import Dict, Any, List, Optional, Union
from botocore.config import Config

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class LLMClient:
    """LLMとのやり取りを行うクライアントクラス"""
    
    def __init__(self, model_id: str = None):
        """
        初期化
        
        Args:
            model_id: 使用するモデルID（デフォルトはNone、その場合はデフォルトモデルが使用される）
        """
        
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            config=Config(
                retries = {
                    'max_attempts': 15,
                    'mode': 'standard'
                }
            )
        )
        self.model_id = model_id or os.environ.get('DEFAULT_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
    
    def invoke_llm(self, 
                  messages: List[Dict[str, str]], 
                  temperature: float = 0.7, 
                  max_tokens: int = 4096,) -> Dict[str, Any]:
        """
        LLMを呼び出す
        
        Args:
            messages: メッセージのリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            
        Returns:
            LLMからのレスポンス
        """
        try:
            # 直接Bedrockを呼び出す
            return self._invoke_via_bedrock(messages, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Error invoking LLM: {str(e)}")
            raise
    
    def _invoke_via_bedrock(self, 
                           messages: List[Dict[str, str]], 
                           temperature: float, 
                           max_tokens: int,) -> Dict[str, Any]:
        """
        直接Bedrockを呼び出す
        
        Args:
            messages: メッセージのリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            
        Returns:
            LLMからのレスポンス（統一された形式）
        """
        # メッセージの形式を確認し、必要に応じて修正
        valid_messages = []
        has_system = False
        system_content = ""
        
        # システムメッセージを抽出
        for msg in messages:
            if msg.get('role') == 'system':
                has_system = True
                system_content += msg.get('content', '') + "\n\n"
        
        # メッセージを構築
        for i, msg in enumerate(messages):
            if msg.get('role') == 'system':
                continue  # システムメッセージはスキップ
            elif msg.get('role') == 'user':
                if i == 0 and has_system:
                    # 最初のユーザーメッセージにシステムプロンプトを追加
                    valid_messages.append({
                        'role': 'user',
                        'content': f"{system_content}\n\n{msg.get('content', '')}"
                    })
                else:
                    valid_messages.append(msg)
            elif msg.get('role') == 'assistant':
                valid_messages.append(msg)
        
        # 有効なメッセージがない場合、エラー
        if not valid_messages:
            raise ValueError("No valid messages provided")
        
        # ロールが交互になっているか確認
        for i in range(1, len(valid_messages)):
            if valid_messages[i]['role'] == valid_messages[i-1]['role']:
                # 同じロールが連続する場合は修正
                if i == len(valid_messages) - 1 and valid_messages[i]['role'] == 'user':
                    # 最後のメッセージがユーザーの場合はOK
                    pass
                else:
                    # それ以外の場合は、ダミーのメッセージを挿入
                    if valid_messages[i]['role'] == 'user':
                        valid_messages.insert(i, {
                            'role': 'assistant',
                            'content': 'I understand. Please continue.'
                        })
                    else:
                        valid_messages.insert(i, {
                            'role': 'user',
                            'content': 'Please continue.'
                        })
        
        # リクエストボディの作成
        request_body = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': valid_messages,
            'temperature': temperature
        }
        
        logger.info(f"Sending request to Bedrock: {json.dumps(request_body)}")
        
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_id,
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
                return {'content': content_text}
            else:
                return {'content': response_body['content']}
        else:
            logger.warning(f"Unexpected response format: {json.dumps(response_body)}")
            return {'content': str(response_body)}