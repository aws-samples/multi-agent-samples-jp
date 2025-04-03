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
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'smajp')
AGENT_STATE_TABLE = os.environ.get('AGENT_STATE_TABLE')
MESSAGE_HISTORY_TABLE = os.environ.get('MESSAGE_HISTORY_TABLE')
ARTIFACTS_BUCKET = os.environ.get('ARTIFACTS_BUCKET')
COMMUNICATION_QUEUE_URL = os.environ.get('COMMUNICATION_QUEUE_URL')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME')

class ProductManager(Agent):
    """プロダクトマネージャーエージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="product_manager",
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
        process_type = input_data.get('process_type', 'analyze_requirement')
        
        try:
            if process_type == 'analyze_requirement':
                return self.analyze_requirement(input_data)
            elif process_type == 'create_user_stories':
                return self.create_user_stories(input_data)
            elif process_type == 'create_competitive_analysis':
                return self.create_competitive_analysis(input_data)
            elif process_type == 'create_product_requirement_doc':
                return self.create_product_requirement_doc(input_data)
            else:
                raise ValueError(f"Unknown process type: {process_type}")
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def analyze_requirement(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        要件を分析
        
        Args:
            input_data: 入力データ
            
        Returns:
            分析結果
        """
        requirement = input_data.get('requirement', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        try:
            # LLMに要件分析を依頼
            messages = [
                {"role": "system", "content": "You are a product manager analyzing a software requirement. Extract key features, target users, and potential challenges."},
                {"role": "user", "content": f"Analyze the following requirement and provide a structured analysis:\n\n{requirement}"}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を保存
            analysis = response.get('content', '')
            analysis_id = str(uuid.uuid4())
            
            # スケーラブルなS3パス構造を使用
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "project_id": project_id,
                    "requirement": requirement, 
                    "analysis": analysis,
                    "user_id": user_id,
                    "created_at": timestamp
                },
                project_id=project_id,
                agent_type="product_manager",
                artifact_type="analysis",
                artifact_id=analysis_id,
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            self.add_to_memory({
                "type": "analysis",
                "id": analysis_id,
                "project_id": project_id,
                "s3_key": s3_key,
                "requirement": requirement,
                "timestamp": timestamp
            })
            self.state = "analysis_completed"
            self.save_state()
            
            # イベントを発行
            self.emit_event(
                detail_type="RequirementAnalysisCompleted",
                detail={
                    "project_id": project_id,
                    "analysis_id": analysis_id,
                    "requirement": requirement,
                    "s3_key": s3_key
                }
            )
            
            return {
                "status": "success",
                "project_id": project_id,
                "analysis_id": analysis_id,
                "analysis": analysis,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in analyze_requirement: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def create_user_stories(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ユーザーストーリーを作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            ユーザーストーリー
        """
        requirement = input_data.get('requirement', '')
        analysis_id = input_data.get('analysis_id', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # 分析結果を取得（あれば）
        analysis = ""
        if analysis_id:
            try:
                # スケーラブルなパス構造を使用
                analysis_data = self.artifacts.download_artifact(
                    project_id=project_id,
                    agent_type="product_manager",
                    artifact_type="analysis",
                    artifact_id=analysis_id,
                    timestamp=timestamp
                )
                analysis = analysis_data.get('analysis', '')
            except Exception as e:
                logger.warning(f"Failed to load analysis: {str(e)}")
        
        # LLMにユーザーストーリーの作成を依頼
        messages = [
            {"role": "system", "content": "You are a product manager creating user stories for a software project. Format each story as 'As a [user type], I want [action] so that [benefit]'."},
            {"role": "user", "content": f"Create user stories for the following requirement:\n\n{requirement}\n\nAnalysis:\n{analysis}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        user_stories = response.get('content', '')
        stories_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement, 
                "analysis_id": analysis_id, 
                "user_stories": user_stories,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="product_manager",
            artifact_type="user_stories",
            artifact_id=stories_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        self.save_artifact(
            content={
                "project_id": project_id,
                "requirement": requirement, 
                "analysis_id": analysis_id, 
                "user_stories": user_stories,
                "user_id": user_id,
                "created_at": input_data.get('timestamp', datetime.utcnow().isoformat())
            },
            key=s3_key
        )
        
        # 状態を更新
        self.add_to_memory({
            "type": "user_stories",
            "id": stories_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "timestamp": timestamp
        })
        self.state = "user_stories_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="UserStoriesCreated",
            detail={
                "project_id": project_id,
                "stories_id": stories_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        # アーキテクトにメッセージを送信
        self.send_message(
            recipient_id="architect",
            content={
                "type": "user_stories_ready",
                "project_id": project_id,
                "stories_id": stories_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "stories_id": stories_id,
            "user_stories": user_stories,
            "s3_key": s3_key
        }
    
    def create_competitive_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        競合分析を作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            競合分析
        """
        requirement = input_data.get('requirement', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # LLMに競合分析の作成を依頼
        messages = [
            {"role": "system", "content": "You are a product manager creating a competitive analysis for a software project. Identify key competitors, their strengths and weaknesses, and market positioning."},
            {"role": "user", "content": f"Create a competitive analysis for the following requirement:\n\n{requirement}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        competitive_analysis = response.get('content', '')
        analysis_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement, 
                "competitive_analysis": competitive_analysis,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="product_manager",
            artifact_type="competitive_analysis",
            artifact_id=analysis_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "competitive_analysis",
            "id": analysis_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "timestamp": timestamp
        })
        self.state = "competitive_analysis_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="CompetitiveAnalysisCreated",
            detail={
                "project_id": project_id,
                "analysis_id": analysis_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "analysis_id": analysis_id,
            "competitive_analysis": competitive_analysis,
            "s3_key": s3_key
        }
    
    def create_product_requirement_doc(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        製品要件書を作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            製品要件書
        """
        requirement = input_data.get('requirement', '')
        stories_id = input_data.get('stories_id', '')
        competitive_analysis_id = input_data.get('competitive_analysis_id', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # ユーザーストーリーと競合分析を取得（あれば）
        user_stories = ""
        competitive_analysis = ""
        
        if stories_id:
            try:
                # スケーラブルなパス構造を使用
                stories_data = self.artifacts.download_artifact(
                    project_id=project_id,
                    agent_type="product_manager",
                    artifact_type="user_stories",
                    artifact_id=stories_id,
                    timestamp=timestamp
                )
                user_stories = stories_data.get('user_stories', '')
            except Exception as e:
                logger.warning(f"Failed to load user stories: {str(e)}")
        
        if competitive_analysis_id:
            try:
                # スケーラブルなパス構造を使用
                analysis_data = self.artifacts.download_artifact(
                    project_id=project_id,
                    agent_type="product_manager",
                    artifact_type="competitive_analysis",
                    artifact_id=competitive_analysis_id,
                    timestamp=timestamp
                )
                competitive_analysis = analysis_data.get('competitive_analysis', '')
            except Exception as e:
                logger.warning(f"Failed to load competitive analysis: {str(e)}")
        
        # LLMに製品要件書の作成を依頼
        messages = [
            {"role": "system", "content": "You are a product manager creating a product requirement document (PRD) for a software project. Include sections for overview, user stories, features, non-functional requirements, and timeline."},
            {"role": "user", "content": f"Create a PRD for the following requirement:\n\n{requirement}\n\nUser Stories:\n{user_stories}\n\nCompetitive Analysis:\n{competitive_analysis}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        prd = response.get('content', '')
        prd_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement,
                "stories_id": stories_id,
                "competitive_analysis_id": competitive_analysis_id,
                "prd": prd,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="product_manager",
            artifact_type="prd",
            artifact_id=prd_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "prd",
            "id": prd_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "timestamp": timestamp
        })
        self.state = "prd_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="ProductRequirementDocCreated",
            detail={
                "project_id": project_id,
                "prd_id": prd_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        # アーキテクトとプロジェクトマネージャーにメッセージを送信
        self.send_message(
            recipient_id="architect",
            content={
                "type": "prd_ready",
                "project_id": project_id,
                "prd_id": prd_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        self.send_message(
            recipient_id="project_manager",
            content={
                "type": "prd_ready",
                "project_id": project_id,
                "prd_id": prd_id,
                "requirement": requirement,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "prd_id": prd_id,
            "prd": prd,
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
                'analyze_requirement': 'analyze_requirement',
                'create_user_stories': 'create_user_stories',
                'create_competitive_analysis': 'create_competitive_analysis',
                'create_product_requirement_doc': 'create_product_requirement_doc',
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
            
            # プロダクトマネージャーエージェントを初期化
            product_manager = ProductManager(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                product_manager.load_state()
            
            # 入力データを処理
            result = product_manager.process(input_data)
            
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
            
            # プロダクトマネージャーエージェントを初期化
            product_manager = ProductManager(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                product_manager.load_state()
            
            # 入力データを処理
            result = product_manager.process(event)
            
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