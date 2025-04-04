import json
import os
import logging
import sys
import uuid
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

class Architect(Agent):
    """アーキテクトエージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="architect",
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
        process_type = input_data.get('process_type', 'create_architecture')
        
        if process_type == 'create_architecture':
            return self.create_architecture(input_data)
        elif process_type == 'create_class_diagram':
            return self.create_class_diagram(input_data)
        elif process_type == 'create_sequence_diagram':
            return self.create_sequence_diagram(input_data)
        elif process_type == 'create_api_design':
            return self.create_api_design(input_data)
        else:
            raise ValueError(f"Unknown process type: {process_type}")
    
    def create_architecture(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        アーキテクチャを作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            アーキテクチャ
        """
        requirement = input_data.get('requirement', '')
        prd_id = input_data.get('prd_id', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # PRDを取得（あれば）
        prd = ""
        if prd_id:
            try:
                # スケーラブルなパス構造を使用
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
        
        # LLMにアーキテクチャの作成を依頼
        messages = [
            {"role": "system", "content": "You are a software architect designing a system architecture. Provide a comprehensive architecture design including components, their interactions, data flow, and technology choices."},
            {"role": "user", "content": f"Create an architecture design for the following requirement:\n\n{requirement}\n\nPRD:\n{prd}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        architecture = response.get('content', '')
        architecture_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement, 
                "prd_id": prd_id, 
                "architecture": architecture,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="architect",
            artifact_type="architecture",
            artifact_id=architecture_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "architecture",
            "id": architecture_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "timestamp": timestamp
        })
        self.state = "architecture_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="ArchitectureCreated",
            detail={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        # エンジニアにメッセージを送信
        self.send_message(
            recipient_id="engineer",
            content={
                "type": "architecture_ready",
                "project_id": project_id,
                "architecture_id": architecture_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "architecture": architecture,
            "s3_key": s3_key
        }
    
    def create_class_diagram(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        クラス図を作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            クラス図
        """
        architecture_id = input_data.get('architecture_id', '')
        project_id = input_data.get('project_id', '')
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not architecture_id:
            raise ValueError("Architecture ID is required")
        
        if not project_id:
            raise ValueError("Project ID is required")
        
        # アーキテクチャを取得
        try:
            architecture_data = self.artifacts.download_artifact(
                project_id=project_id,
                agent_type="architect",
                artifact_type="architecture",
                artifact_id=architecture_id,
                timestamp=timestamp
            )
            architecture = architecture_data.get('architecture', '')
            requirement = architecture_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load architecture: {str(e)}")
            raise ValueError(f"Failed to load architecture: {str(e)}")
        
        # LLMにクラス図の作成を依頼
        messages = [
            {"role": "system", "content": "You are a software architect creating a class diagram in PlantUML format. Define classes, their attributes, methods, and relationships."},
            {"role": "user", "content": f"Create a class diagram in PlantUML format for the following architecture:\n\n{architecture}\n\nRequirement:\n{requirement}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        class_diagram = response.get('content', '')
        diagram_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "architecture_id": architecture_id, 
                "class_diagram": class_diagram,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="architect",
            artifact_type="class_diagram",
            artifact_id=diagram_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "class_diagram",
            "id": diagram_id,
            "architecture_id": architecture_id,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "class_diagram_created"
        self.save_state()
        
        return {
            "status": "success",
            "diagram_id": diagram_id,
            "class_diagram": class_diagram,
            "s3_key": s3_key
        }
    
    def create_sequence_diagram(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        シーケンス図を作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            シーケンス図
        """
        architecture_id = input_data.get('architecture_id', '')
        use_case = input_data.get('use_case', '')
        project_id = input_data.get('project_id', '')
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not architecture_id:
            raise ValueError("Architecture ID is required")
        
        if not use_case:
            raise ValueError("Use case is required")
            
        if not project_id:
            raise ValueError("Project ID is required")
        
        # アーキテクチャを取得
        try:
            architecture_data = self.artifacts.download_artifact(
                project_id=project_id,
                agent_type="architect",
                artifact_type="architecture",
                artifact_id=architecture_id,
                timestamp=timestamp
            )
            architecture = architecture_data.get('architecture', '')
            requirement = architecture_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load architecture: {str(e)}")
            raise ValueError(f"Failed to load architecture: {str(e)}")
        
        # LLMにシーケンス図の作成を依頼
        messages = [
            {"role": "system", "content": "You are a software architect creating a sequence diagram in PlantUML format. Define actors, components, and their interactions over time."},
            {"role": "user", "content": f"Create a sequence diagram in PlantUML format for the following use case: '{use_case}'\n\nArchitecture:\n{architecture}\n\nRequirement:\n{requirement}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        sequence_diagram = response.get('content', '')
        diagram_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "architecture_id": architecture_id, 
                "use_case": use_case,
                "sequence_diagram": sequence_diagram,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="architect",
            artifact_type="sequence_diagram",
            artifact_id=diagram_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "sequence_diagram",
            "id": diagram_id,
            "architecture_id": architecture_id,
            "use_case": use_case,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "sequence_diagram_created"
        self.save_state()
        
        return {
            "status": "success",
            "diagram_id": diagram_id,
            "sequence_diagram": sequence_diagram,
            "s3_key": s3_key
        }
    
    def create_api_design(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API設計を作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            API設計
        """
        architecture_id = input_data.get('architecture_id', '')
        project_id = input_data.get('project_id', '')
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not architecture_id:
            raise ValueError("Architecture ID is required")
            
        if not project_id:
            raise ValueError("Project ID is required")
        
        # アーキテクチャを取得
        try:
            architecture_data = self.artifacts.download_artifact(
                project_id=project_id,
                agent_type="architect",
                artifact_type="architecture",
                artifact_id=architecture_id,
                timestamp=timestamp
            )
            architecture = architecture_data.get('architecture', '')
            requirement = architecture_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load architecture: {str(e)}")
            raise ValueError(f"Failed to load architecture: {str(e)}")
        
        # LLMにAPI設計の作成を依頼
        messages = [
            {"role": "system", "content": "You are a software architect designing RESTful APIs. Define endpoints, HTTP methods, request/response formats, and status codes in OpenAPI/Swagger format."},
            {"role": "user", "content": f"Create an API design in OpenAPI/Swagger format for the following architecture:\n\n{architecture}\n\nRequirement:\n{requirement}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        api_design = response.get('content', '')
        design_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "architecture_id": architecture_id, 
                "api_design": api_design,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="architect",
            artifact_type="api_design",
            artifact_id=design_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "api_design",
            "id": design_id,
            "architecture_id": architecture_id,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "api_design_created"
        self.save_state()
        
        return {
            "status": "success",
            "design_id": design_id,
            "api_design": api_design,
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
                'create_architecture': 'create_architecture',
                'create_class_diagram': 'create_class_diagram',
                'create_sequence_diagram': 'create_sequence_diagram',
                'create_api_design': 'create_api_design',
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
            
            # アーキテクトエージェントを初期化
            architect = Architect(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                architect.load_state()
            
            # 入力データを処理
            result = architect.process(input_data)
            
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
            
            # アーキテクトエージェントを初期化
            architect = Architect(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                architect.load_state()
            
            # 入力データを処理
            result = architect.process(event)
            
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