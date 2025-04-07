import json
import os
import logging
import sys
import uuid
import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional

# 共通ライブラリのパスを追加
sys.path.append('/opt/python')
from agent_base import Agent
from llm_client import LLMClient

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数
ENV_NAME = os.environ.get('ENV_NAME', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'masjp')
AGENT_STATE_TABLE = os.environ.get('AGENT_STATE_TABLE')
MESSAGE_HISTORY_TABLE = os.environ.get('MESSAGE_HISTORY_TABLE')
ARTIFACTS_BUCKET = os.environ.get('ARTIFACTS_BUCKET')
COMMUNICATION_QUEUE_URL = os.environ.get('COMMUNICATION_QUEUE_URL')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME')
CODE_EXECUTION_PROJECT = os.environ.get('CODE_EXECUTION_PROJECT')

class Engineer(Agent):
    """エンジニアエージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="engineer",
            agent_state_table=AGENT_STATE_TABLE,
            message_history_table=MESSAGE_HISTORY_TABLE,
            artifacts_bucket=ARTIFACTS_BUCKET,
            communication_queue_url=COMMUNICATION_QUEUE_URL,
            event_bus_name=EVENT_BUS_NAME
        )
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        入力データを処理
        
        Args:
            input_data: 入力データ
            
        Returns:
            処理結果
        """
        logger.info(f"Processing input: {json.dumps(input_data)}")
        
        # 処理タイプに基づいて適切なメソッドを呼び出す
        process_type = input_data.get('process_type', 'implement_code')
        
        try:
            if process_type == 'implement_code':
                return self.implement_code(input_data)
            elif process_type == 'review_code':
                return self.review_code(input_data)
            elif process_type == 'fix_bugs':
                return self.fix_bugs(input_data)
            else:
                raise ValueError(f"Unknown process type: {process_type}")
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def implement_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        コードを実装
        
        Args:
            input_data: 入力データ
            
        Returns:
            実装結果
        """
        requirement = input_data.get('requirement', '')
        prd_id = input_data.get('prd_id', '')
        architecture_id = input_data.get('architecture_id', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        user_id = input_data.get('user_id', 'default_user')
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # PRDとアーキテクチャを取得（あれば）
        prd = ""
        architecture = ""
        
        if prd_id:
            try:
                prd_data = self.artifacts.download_artifact(
                    project_id=project_id,
                    agent_type="product_manager",
                    artifact_type="prd",
                    artifact_id=prd_id,
                    timestamp=timestamp
                )
                prd = prd_data.get('prd', '')
            except Exception as e:
                logger.warning(f"Failed to load PRD: {str(e)}")
        
        if architecture_id:
            try:
                architecture_data = self.artifacts.download_artifact(
                    project_id=project_id,
                    agent_type="architect",
                    artifact_type="architecture",
                    artifact_id=architecture_id,
                    timestamp=timestamp
                )
                architecture = architecture_data.get('architecture', '')
            except Exception as e:
                logger.warning(f"Failed to load architecture: {str(e)}")
        
        # LLMにコード実装を依頼
        messages = [
            {"role": "system", "content": "You are a software engineer implementing code based on requirements and architecture design. Provide well-structured, documented, and tested code."},
            {"role": "user", "content": f"Implement code for the following requirement:\n\n{requirement}\n\nPRD:\n{prd}\n\nArchitecture:\n{architecture}\n\nProvide complete implementation with proper documentation, error handling, and unit tests."}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        implementation = response.get('content', '')
        implementation_id = str(uuid.uuid4())
        
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement,
                "prd_id": prd_id,
                "architecture_id": architecture_id,
                "implementation": implementation,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="engineer",
            artifact_type="implementation",
            artifact_id=implementation_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "implementation",
            "id": implementation_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "timestamp": timestamp
        })
        self.state = "code_implemented"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="CodeImplemented",
            detail={
                "project_id": project_id,
                "implementation_id": implementation_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "implementation_id": implementation_id,
            "implementation": implementation,
            "s3_key": s3_key
        }
    
    def review_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        コードをレビュー
        
        Args:
            input_data: 入力データ
            
        Returns:
            レビュー結果
        """
        implementation_id = input_data.get('implementation_id', '')
        project_id = input_data.get('project_id', '')
        requirement = input_data.get('requirement', '')
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not implementation_id:
            raise ValueError("Implementation ID is required")
            
        if not project_id:
            raise ValueError("Project ID is required")
        
        # 実装を取得
        try:
            implementation_data = self.artifacts.download_artifact(
                project_id=project_id,
                agent_type="engineer",
                artifact_type="implementation",
                artifact_id=implementation_id,
                timestamp=timestamp
            )
            implementation = implementation_data.get('implementation', '')
            requirement = implementation_data.get('requirement', requirement)
        except Exception as e:
            logger.warning(f"Failed to load implementation: {str(e)}")
            raise ValueError(f"Failed to load implementation: {str(e)}")
        
        # LLMにコードレビューを依頼
        messages = [
            {"role": "system", "content": "You are a senior software engineer reviewing code. Evaluate code quality, identify bugs, suggest improvements, and check if the code meets requirements."},
            {"role": "user", "content": f"Review the following code implementation for the requirement:\n\nRequirement:\n{requirement}\n\nImplementation:\n{implementation}\n\nProvide a detailed review including code quality, potential bugs, security issues, and improvement suggestions."}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        review = response.get('content', '')
        review_id = str(uuid.uuid4())
        
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "implementation_id": implementation_id,
                "requirement": requirement,
                "review": review,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="engineer",
            artifact_type="review",
            artifact_id=review_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "review",
            "id": review_id,
            "implementation_id": implementation_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "code_reviewed"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="CodeReviewed",
            detail={
                "project_id": project_id,
                "review_id": review_id,
                "implementation_id": implementation_id,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "review_id": review_id,
            "review": review,
            "s3_key": s3_key
        }
    
    def fix_bugs(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        バグを修正
        
        Args:
            input_data: 入力データ
            
        Returns:
            修正結果
        """
        implementation_id = input_data.get('implementation_id', '')
        review_id = input_data.get('review_id', '')
        project_id = input_data.get('project_id', '')
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not implementation_id:
            raise ValueError("Implementation ID is required")
            
        if not project_id:
            raise ValueError("Project ID is required")
        
        # 実装を取得
        try:
            implementation_data = self.artifacts.download_artifact(
                project_id=project_id,
                agent_type="engineer",
                artifact_type="implementation",
                artifact_id=implementation_id,
                timestamp=timestamp
            )
            implementation = implementation_data.get('implementation', '')
            requirement = implementation_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load implementation: {str(e)}")
            raise ValueError(f"Failed to load implementation: {str(e)}")
        
        # レビューを取得（あれば）
        review = ""
        if review_id:
            try:
                review_data = self.artifacts.download_artifact(
                    project_id=project_id,
                    agent_type="engineer",
                    artifact_type="review",
                    artifact_id=review_id,
                    timestamp=timestamp
                )
                review = review_data.get('review', '')
            except Exception as e:
                logger.warning(f"Failed to load review: {str(e)}")
        
        # LLMにバグ修正を依頼
        messages = [
            {"role": "system", "content": "You are a software engineer fixing bugs in code. Analyze the issues, provide solutions, and ensure the code meets requirements."},
            {"role": "user", "content": f"Fix the bugs in the following code implementation:\n\nRequirement:\n{requirement}\n\nImplementation:\n{implementation}\n\nReview:\n{review}\n\nProvide the fixed implementation with explanations of the changes made."}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        fixed_implementation = response.get('content', '')
        fixed_id = str(uuid.uuid4())
        
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "implementation_id": implementation_id,
                "review_id": review_id,
                "requirement": requirement,
                "fixed_implementation": fixed_implementation,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="engineer",
            artifact_type="fixed_implementation",
            artifact_id=fixed_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "fixed_implementation",
            "id": fixed_id,
            "implementation_id": implementation_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "bugs_fixed"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="BugsFixed",
            detail={
                "project_id": project_id,
                "fixed_id": fixed_id,
                "implementation_id": implementation_id,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "fixed_id": fixed_id,
            "fixed_implementation": fixed_implementation,
            "s3_key": s3_key
        }

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda関数のハンドラー
    
    Args:
        event: Lambda関数のイベントデータ
        context: Lambda関数のコンテキスト
        
    Returns:
        処理結果
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Bedrock Agent呼び出しの場合
        if 'actionGroup' in event and 'function' in event:
            function = event['function']
            action_group = event['actionGroup']
            
            # 関数名とprocess_typeの対応付け
            function_to_process = {
                'implement_code': 'implement_code',
                'review_code': 'review_code',
                'fix_bugs': 'fix_bugs',
            }
            
            # 入力データの構築
            input_data = {
                'process_type': function_to_process.get(function, function.lower()),
            }
            
            # パラメータの抽出と変換
            params = event.get('parameters', [])
            for param in params:
                name = param['name']
                value = param['value']
                input_data[name] = value
            
            # エージェントIDを取得
            agent_id = input_data.get('agent_id')
            
            # sessionIdをproject_idとして使用
            if 'sessionId' in event:
                input_data['project_id'] = event['sessionId']
                logger.info(f"Using sessionId as project_id: {event['sessionId']}")
            
            # エンジニアエージェントを初期化
            engineer = Engineer(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                engineer.load_state()
            
            # 入力データを処理
            result = engineer.process(input_data)
            
            # Bedrock Agent形式でレスポンスを返す
            response_body = {
                "TEXT": {
                    "body": json.dumps(result, ensure_ascii=False)
                }
            }
            
            return {
                'messageVersion': '1.0',
                'response': {
                    'actionGroup': action_group,
                    'function': function,
                    'functionResponse': {
                        'responseBody': response_body
                    }
                }
            }
        
        # 従来のStep Functions呼び出しの場合
        else:
            # エージェントIDを取得
            agent_id = event.get('agent_id')
            
            # エンジニアエージェントを初期化
            engineer = Engineer(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                engineer.load_state()
            
            # 入力データを処理
            result = engineer.process(event)
            
            # 結果を直接返す
            return result
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        
        # Bedrock Agent呼び出しの場合のエラーレスポンス
        if 'actionGroup' in event and 'function' in event:
            error_body = {
                "TEXT": {
                    "body": json.dumps({
                        'error': str(e),
                        'status': 'failed'
                    }, ensure_ascii=False)
                }
            }
            
            return {
                'messageVersion': '1.0',
                'response': {
                    'actionGroup': event.get('actionGroup', ''),
                    'function': event.get('function', ''),
                    'functionResponse': {
                        'responseBody': error_body
                    }
                }
            }
        
        # 従来の呼び出しの場合のエラーレスポンス
        return {'error': str(e), 'status': 'failed'}