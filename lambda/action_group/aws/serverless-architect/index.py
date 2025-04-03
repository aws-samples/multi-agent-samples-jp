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

class ServerlessArchitect(Agent):
    """ServerlessArchitectエージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="serverless_architect",
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
        process_type = input_data.get('process_type', 'design_serverless_architecture')
        
        try:
            if process_type == 'design_serverless_architecture':
                return self.design_serverless_architecture(input_data)
            elif process_type == 'design_event_driven_architecture':
                return self.design_event_driven_architecture(input_data)
            elif process_type == 'design_api_gateway':
                return self.design_api_gateway(input_data)
            elif process_type == 'optimize_lambda_functions':
                return self.optimize_lambda_functions(input_data)
            elif process_type == 'design_step_functions_workflow':
                return self.design_step_functions_workflow(input_data)
            else:
                raise ValueError(f"Unknown process type: {process_type}")
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def design_serverless_architecture(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        サーバーレスアーキテクチャを設計
        
        Args:
            input_data: 入力データ
            
        Returns:
            サーバーレスアーキテクチャ設計
        """
        requirement = input_data.get('requirement', '')
        application_type = input_data.get('application_type', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # LLMにサーバーレスアーキテクチャの設計を依頼
        messages = [
            {"role": "system", "content": """You are a serverless architecture specialist focusing on AWS. Design a comprehensive serverless architecture based on requirements.
Include:
1. Overall architecture diagram (in text format using ASCII art or describe it clearly)
2. AWS serverless services selection with justification
3. Detailed component descriptions (Lambda functions, API Gateway, DynamoDB, etc.)
4. Data flow and integration patterns
5. Authentication and authorization approach
6. Scaling and performance considerations
7. Cost optimization strategies
8. Security best practices
9. Monitoring and observability recommendations

Format your response as a detailed architecture document with clear sections for each component."""},
            {"role": "user", "content": f"Design a serverless architecture for the following requirement:\n\n{requirement}" + 
             (f"\nApplication type: {application_type}" if application_type else "")}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        serverless_architecture = response.get('content', '')
        architecture_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement,
                "application_type": application_type,
                "serverless_architecture": serverless_architecture,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="serverless_architect",
            artifact_type="serverless_architecture",
            artifact_id=architecture_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "serverless_architecture",
            "id": architecture_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "application_type": application_type,
            "timestamp": timestamp
        })
        self.state = "serverless_architecture_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="ServerlessArchitectureCreated",
            detail={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "requirement": requirement,
                "application_type": application_type,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "serverless_architecture": serverless_architecture,
            "s3_key": s3_key
        }
    
    def design_event_driven_architecture(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        イベント駆動型アーキテクチャを設計
        
        Args:
            input_data: 入力データ
            
        Returns:
            イベント駆動型アーキテクチャ設計
        """
        requirement = input_data.get('requirement', '')
        event_sources = input_data.get('event_sources', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # LLMにイベント駆動型アーキテクチャの設計を依頼
        messages = [
            {"role": "system", "content": """You are an event-driven architecture specialist focusing on AWS serverless services. Design a comprehensive event-driven architecture based on requirements.
Include:
1. Event sources and producers
2. Event routing and filtering mechanisms
3. Event consumers and handlers
4. AWS service selection (EventBridge, SNS, SQS, Lambda, etc.)
5. Event schema design and validation
6. Error handling and dead-letter queues
7. Event replay and idempotency patterns
8. Monitoring and observability
9. Scaling considerations

Format your response as a detailed architecture document with clear sections for each component."""},
            {"role": "user", "content": f"Design an event-driven serverless architecture for the following requirement:\n\n{requirement}" + 
             (f"\nEvent sources: {event_sources}" if event_sources else "")}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        event_architecture = response.get('content', '')
        architecture_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement,
                "event_sources": event_sources,
                "event_architecture": event_architecture,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="serverless_architect",
            artifact_type="event_architecture",
            artifact_id=architecture_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "event_architecture",
            "id": architecture_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "event_sources": event_sources,
            "timestamp": timestamp
        })
        self.state = "event_architecture_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="EventDrivenArchitectureCreated",
            detail={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "requirement": requirement,
                "event_sources": event_sources,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "event_architecture": event_architecture,
            "s3_key": s3_key
        }
    
    def design_api_gateway(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API Gatewayを設計
        
        Args:
            input_data: 入力データ
            
        Returns:
            API Gateway設計
        """
        requirement = input_data.get('requirement', '')
        api_type = input_data.get('api_type', 'rest')
        authentication_type = input_data.get('authentication_type', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # LLMにAPI Gateway設計を依頼
        messages = [
            {"role": "system", "content": f"""You are an API design specialist focusing on AWS API Gateway. Design a comprehensive {api_type.upper()} API based on requirements.
Include:
1. API resources and endpoints structure
2. HTTP methods and status codes
3. Request/response models and schemas
4. Authentication and authorization mechanism
5. API throttling and quota settings
6. CORS configuration
7. Integration with backend services (Lambda, etc.)
8. Error handling patterns
9. API documentation (Swagger/OpenAPI)
10. Deployment strategy (stages, canary deployments)

Format your response as a detailed API design document with clear sections for each component."""},
            {"role": "user", "content": f"Design an {api_type.upper()} API using API Gateway for the following requirement:\n\n{requirement}" + 
             (f"\nAuthentication type: {authentication_type}" if authentication_type else "")}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        api_design = response.get('content', '')
        api_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement,
                "api_type": api_type,
                "authentication_type": authentication_type,
                "api_design": api_design,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="serverless_architect",
            artifact_type="api_design",
            artifact_id=api_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "api_design",
            "id": api_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "api_type": api_type,
            "authentication_type": authentication_type,
            "timestamp": timestamp
        })
        self.state = "api_design_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="ApiGatewayDesignCreated",
            detail={
                "project_id": project_id,
                "api_id": api_id,
                "requirement": requirement,
                "api_type": api_type,
                "authentication_type": authentication_type,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "api_id": api_id,
            "api_design": api_design,
            "s3_key": s3_key
        }
    
    def optimize_lambda_functions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lambda関数を最適化
        
        Args:
            input_data: 入力データ
            
        Returns:
            Lambda関数の最適化提案
        """
        function_code = input_data.get('function_code', '')
        runtime = input_data.get('runtime', '')
        optimization_focus = input_data.get('optimization_focus', 'all')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not function_code:
            raise ValueError("Function code is required")
        
        if not runtime:
            raise ValueError("Runtime is required")
        
        # LLMにLambda関数の最適化を依頼
        messages = [
            {"role": "system", "content": f"""You are an AWS Lambda optimization specialist. Analyze the provided Lambda function code and provide optimization recommendations focusing on: {optimization_focus}.
Include:
1. Performance optimization (cold start, execution time, memory usage)
2. Cost optimization (memory settings, execution duration)
3. Security best practices (IAM permissions, environment variables)
4. Code quality and maintainability
5. Error handling and resilience
6. Logging and monitoring
7. Specific {runtime} runtime optimizations
8. Implementation examples for key recommendations

Format your response as a structured optimization report with clear sections for each area."""},
            {"role": "user", "content": f"Optimize the following Lambda function written in {runtime}:\n\n```\n{function_code}\n```\n\nFocus on: {optimization_focus}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        optimization = response.get('content', '')
        optimization_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "function_code": function_code,
                "runtime": runtime,
                "optimization_focus": optimization_focus,
                "optimization": optimization,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="serverless_architect",
            artifact_type="lambda_optimization",
            artifact_id=optimization_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "lambda_optimization",
            "id": optimization_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "runtime": runtime,
            "optimization_focus": optimization_focus,
            "timestamp": timestamp
        })
        self.state = "lambda_optimization_created"
        self.save_state()
        
        return {
            "status": "success",
            "project_id": project_id,
            "optimization_id": optimization_id,
            "optimization": optimization,
            "s3_key": s3_key
        }
    
    def design_step_functions_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step Functionsワークフローを設計
        
        Args:
            input_data: 入力データ
            
        Returns:
            Step Functionsワークフロー設計
        """
        requirement = input_data.get('requirement', '')
        workflow_type = input_data.get('workflow_type', 'standard')
        integration_services = input_data.get('integration_services', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # LLMにStep Functionsワークフローの設計を依頼
        messages = [
            {"role": "system", "content": f"""You are an AWS Step Functions workflow specialist. Design a comprehensive {workflow_type} Step Functions workflow based on requirements.
Include:
1. State machine diagram (in text format using ASCII art or describe it clearly)
2. State machine definition in Amazon States Language (JSON)
3. Detailed state descriptions and transitions
4. Integration with AWS services
5. Error handling and retry strategies
6. Input/output processing and filtering
7. Execution management (timeouts, heartbeats)
8. Monitoring and logging approach
9. Best practices and optimization tips

Format your response as a detailed workflow design document with clear sections for each component."""},
            {"role": "user", "content": f"Design a {workflow_type} Step Functions workflow for the following requirement:\n\n{requirement}" + 
             (f"\nIntegration services: {integration_services}" if integration_services else "")}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        workflow_design = response.get('content', '')
        workflow_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement,
                "workflow_type": workflow_type,
                "integration_services": integration_services,
                "workflow_design": workflow_design,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="serverless_architect",
            artifact_type="step_functions_workflow",
            artifact_id=workflow_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "step_functions_workflow",
            "id": workflow_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "workflow_type": workflow_type,
            "integration_services": integration_services,
            "timestamp": timestamp
        })
        self.state = "step_functions_workflow_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="StepFunctionsWorkflowCreated",
            detail={
                "project_id": project_id,
                "workflow_id": workflow_id,
                "requirement": requirement,
                "workflow_type": workflow_type,
                "integration_services": integration_services,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "workflow_id": workflow_id,
            "workflow_design": workflow_design,
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
                'design_serverless_architecture': 'design_serverless_architecture',
                'design_event_driven_architecture': 'design_event_driven_architecture',
                'design_api_gateway': 'design_api_gateway',
                'optimize_lambda_functions': 'optimize_lambda_functions',
                'design_step_functions_workflow': 'design_step_functions_workflow',
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
            
            # ServerlessArchitectエージェントを初期化
            serverless_architect = ServerlessArchitect(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                serverless_architect.load_state()
            
            # 入力データを処理
            result = serverless_architect.process(input_data)
            
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
            
            # ServerlessArchitectエージェントを初期化
            serverless_architect = ServerlessArchitect(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                serverless_architect.load_state()
            
            # 入力データを処理
            result = serverless_architect.process(event)
            
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