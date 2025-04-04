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

class CloudArchitect(Agent):
    """クラウドアーキテクトエージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="cloud_architect",
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
        process_type = input_data.get('process_type', 'design_cloud_architecture')
        
        try:
            if process_type == 'design_cloud_architecture':
                return self.design_cloud_architecture(input_data)
            elif process_type == 'evaluate_architecture':
                return self.evaluate_architecture(input_data)
            elif process_type == 'create_infrastructure_diagram':
                return self.create_infrastructure_diagram(input_data)
            elif process_type == 'optimize_cost':
                return self.optimize_cost(input_data)
            elif process_type == 'design_disaster_recovery':
                return self.design_disaster_recovery(input_data)
            elif process_type == 'analyze_cfn_failure':
                return self.analyze_cfn_failure(input_data)
            else:
                raise ValueError(f"Unknown process type: {process_type}")
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def design_cloud_architecture(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AWSクラウドアーキテクチャを設計
        
        Args:
            input_data: 入力データ
            
        Returns:
            クラウドアーキテクチャ
        """
        requirement = input_data.get('requirement', '')
        architecture_type = input_data.get('architecture_type', '')
        project_id = input_data.get('project_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not requirement:
            raise ValueError("Requirement is required")
        
        # LLMにクラウドアーキテクチャの設計を依頼
        messages = [
            {"role": "system", "content": """You are a cloud architect specializing in AWS. Design a comprehensive cloud architecture based on requirements. 
Include:
1. AWS services selection with justification
2. Network architecture (VPC, subnets, security groups)
3. Compute resources (EC2, Lambda, ECS, etc.)
4. Storage solutions (S3, EBS, EFS, etc.)
5. Database choices (RDS, DynamoDB, etc.)
6. Security considerations (IAM, KMS, etc.)
7. High availability and disaster recovery approach
8. Cost optimization strategies
9. Monitoring and logging setup (CloudWatch, etc.)

Format your response as a detailed architecture document with sections for each component."""},
            {"role": "user", "content": f"Design an AWS cloud architecture for the following requirement:\n\n{requirement}" + (f"\nPreferred architecture type: {architecture_type}" if architecture_type else "")}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        cloud_architecture = response.get('content', '')
        architecture_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "requirement": requirement,
                "architecture_type": architecture_type,
                "cloud_architecture": cloud_architecture,
                "user_id": user_id,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="cloud_architect",
            artifact_type="cloud_architecture",
            artifact_id=architecture_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "cloud_architecture",
            "id": architecture_id,
            "project_id": project_id,
            "s3_key": s3_key,
            "requirement": requirement,
            "architecture_type": architecture_type,
            "timestamp": timestamp
        })
        self.state = "cloud_architecture_created"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="CloudArchitectureCreated",
            detail={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "requirement": requirement,
                "architecture_type": architecture_type,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "cloud_architecture": cloud_architecture,
            "s3_key": s3_key
        }
    
    def evaluate_architecture(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        AWS Well-Architected Frameworkに基づいてクラウドアーキテクチャを評価
        
        Args:
            input_data: 入力データ
            
        Returns:
            評価結果
        """
        architecture_id = input_data.get('architecture_id', '')
        pillars = input_data.get('pillars', '')
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
                agent_type="cloud_architect",
                artifact_type="cloud_architecture",
                artifact_id=architecture_id,
                timestamp=timestamp
            )
            cloud_architecture = architecture_data.get('cloud_architecture', '')
            requirement = architecture_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load cloud architecture: {str(e)}")
            raise ValueError(f"Failed to load cloud architecture: {str(e)}")
        
        # 評価する柱を決定
        all_pillars = ["operational-excellence", "security", "reliability", "performance-efficiency", "cost-optimization", "sustainability"]
        selected_pillars = pillars.split(',') if pillars else all_pillars
        
        # LLMにアーキテクチャの評価を依頼
        messages = [
            {"role": "system", "content": f"""You are a cloud architect specializing in AWS Well-Architected Framework reviews. 
Evaluate the provided architecture against the following pillars: {', '.join(selected_pillars)}.

For each pillar:
1. Identify strengths
2. Identify weaknesses and risks
3. Provide specific recommendations for improvement
4. Rate the architecture on a scale of 1-5 for this pillar

Format your response as a structured evaluation report with sections for each pillar."""},
            {"role": "user", "content": f"Evaluate the following AWS cloud architecture against the Well-Architected Framework:\n\n{cloud_architecture}\n\nOriginal requirement:\n{requirement}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        evaluation = response.get('content', '')
        evaluation_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "pillars": pillars,
                "evaluation": evaluation,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="cloud_architect",
            artifact_type="architecture_evaluation",
            artifact_id=evaluation_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "architecture_evaluation",
            "id": evaluation_id,
            "project_id": project_id,
            "architecture_id": architecture_id,
            "s3_key": s3_key,
            "pillars": pillars,
            "timestamp": timestamp
        })
        self.state = "architecture_evaluated"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="ArchitectureEvaluationCompleted",
            detail={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "evaluation_id": evaluation_id,
                "pillars": pillars,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "evaluation_id": evaluation_id,
            "evaluation": evaluation,
            "s3_key": s3_key
        }
    
    def create_infrastructure_diagram(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        インフラストラクチャ図を作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            インフラストラクチャ図
        """
        architecture_id = input_data.get('architecture_id', '')
        diagram_type = input_data.get('diagram_type', 'high-level')
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
                agent_type="cloud_architect",
                artifact_type="cloud_architecture",
                artifact_id=architecture_id,
                timestamp=timestamp
            )
            cloud_architecture = architecture_data.get('cloud_architecture', '')
            requirement = architecture_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load cloud architecture: {str(e)}")
            raise ValueError(f"Failed to load cloud architecture: {str(e)}")
        
        # LLMにインフラストラクチャ図の作成を依頼
        messages = [
            {"role": "system", "content": f"""You are a cloud architect specializing in AWS infrastructure diagrams. 
Create a {diagram_type} infrastructure diagram for the provided architecture using Mermaid syntax.

For AWS architecture diagrams in Mermaid:
1. Use flowchart or graph syntax
2. Represent AWS services with appropriate labels
3. Show connections and data flow between services
4. Group related services (e.g., by VPC, availability zone)
5. Include a legend explaining symbols

Ensure the diagram is clear, readable, and accurately represents the architecture."""},
            {"role": "user", "content": f"Create a {diagram_type} infrastructure diagram in Mermaid syntax for the following AWS cloud architecture:\n\n{cloud_architecture}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        diagram = response.get('content', '')
        diagram_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "diagram_type": diagram_type,
                "infrastructure_diagram": diagram,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="cloud_architect",
            artifact_type="infrastructure_diagram",
            artifact_id=diagram_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "infrastructure_diagram",
            "id": diagram_id,
            "project_id": project_id,
            "architecture_id": architecture_id,
            "diagram_type": diagram_type,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "infrastructure_diagram_created"
        self.save_state()
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "diagram_id": diagram_id,
            "infrastructure_diagram": diagram,
            "s3_key": s3_key
        }
    
    def optimize_cost(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        コスト最適化分析を行う
        
        Args:
            input_data: 入力データ
            
        Returns:
            コスト最適化分析結果
        """
        architecture_id = input_data.get('architecture_id', '')
        monthly_budget = input_data.get('monthly_budget', '')
        optimization_focus = input_data.get('optimization_focus', 'all')
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
                agent_type="cloud_architect",
                artifact_type="cloud_architecture",
                artifact_id=architecture_id,
                timestamp=timestamp
            )
            cloud_architecture = architecture_data.get('cloud_architecture', '')
            requirement = architecture_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load cloud architecture: {str(e)}")
            raise ValueError(f"Failed to load cloud architecture: {str(e)}")
        
        # LLMにコスト最適化分析を依頼
        messages = [
            {"role": "system", "content": f"""You are a cloud architect specializing in AWS cost optimization. 
Analyze the provided architecture and identify cost optimization opportunities with a focus on: {optimization_focus}.
{f'The target monthly budget is: ${monthly_budget}' if monthly_budget else ''}

Include in your analysis:
1. Current estimated cost breakdown by service
2. Specific cost optimization recommendations
3. Estimated savings for each recommendation
4. Implementation complexity (Low/Medium/High)
5. Potential impact on performance, reliability, or security
6. Prioritized action plan

Format your response as a structured cost optimization report."""},
            {"role": "user", "content": f"Analyze and optimize costs for the following AWS cloud architecture:\n\n{cloud_architecture}\n\nOriginal requirement:\n{requirement}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        cost_optimization = response.get('content', '')
        optimization_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "monthly_budget": monthly_budget,
                "optimization_focus": optimization_focus,
                "cost_optimization": cost_optimization,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="cloud_architect",
            artifact_type="cost_optimization",
            artifact_id=optimization_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "cost_optimization",
            "id": optimization_id,
            "project_id": project_id,
            "architecture_id": architecture_id,
            "monthly_budget": monthly_budget,
            "optimization_focus": optimization_focus,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "cost_optimization_completed"
        self.save_state()
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "optimization_id": optimization_id,
            "cost_optimization": cost_optimization,
            "s3_key": s3_key
        }
    
    def design_disaster_recovery(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        災害復旧（DR）戦略を設計
        
        Args:
            input_data: 入力データ
            
        Returns:
            災害復旧戦略
        """
        architecture_id = input_data.get('architecture_id', '')
        rpo_hours = input_data.get('rpo_hours', '')
        rto_hours = input_data.get('rto_hours', '')
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
                agent_type="cloud_architect",
                artifact_type="cloud_architecture",
                artifact_id=architecture_id,
                timestamp=timestamp
            )
            cloud_architecture = architecture_data.get('cloud_architecture', '')
            requirement = architecture_data.get('requirement', '')
        except Exception as e:
            logger.warning(f"Failed to load cloud architecture: {str(e)}")
            raise ValueError(f"Failed to load cloud architecture: {str(e)}")
        
        # RPO/RTO情報を追加
        rpo_rto_info = ""
        if rpo_hours:
            rpo_rto_info += f"Target Recovery Point Objective (RPO): {rpo_hours} hours\n"
        if rto_hours:
            rpo_rto_info += f"Target Recovery Time Objective (RTO): {rto_hours} hours\n"
        
        # LLMに災害復旧戦略の設計を依頼
        messages = [
            {"role": "system", "content": f"""You are a cloud architect specializing in AWS disaster recovery planning. 
Design a comprehensive disaster recovery strategy for the provided architecture.
{rpo_rto_info}

Include in your strategy:
1. DR approach (Backup & Restore, Pilot Light, Warm Standby, or Multi-Site Active/Active)
2. Backup strategy and retention policy
3. Data replication approach
4. Failover mechanism and process
5. Recovery procedures
6. Testing strategy
7. Estimated costs
8. Implementation roadmap

Format your response as a structured disaster recovery plan."""},
            {"role": "user", "content": f"Design a disaster recovery strategy for the following AWS cloud architecture:\n\n{cloud_architecture}\n\nOriginal requirement:\n{requirement}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        dr_strategy = response.get('content', '')
        dr_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "project_id": project_id,
                "architecture_id": architecture_id,
                "rpo_hours": rpo_hours,
                "rto_hours": rto_hours,
                "dr_strategy": dr_strategy,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="cloud_architect",
            artifact_type="disaster_recovery",
            artifact_id=dr_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "disaster_recovery",
            "id": dr_id,
            "project_id": project_id,
            "architecture_id": architecture_id,
            "rpo_hours": rpo_hours,
            "rto_hours": rto_hours,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "disaster_recovery_designed"
        self.save_state()
        
        return {
            "status": "success",
            "project_id": project_id,
            "architecture_id": architecture_id,
            "dr_id": dr_id,
            "dr_strategy": dr_strategy,
            "s3_key": s3_key
        }
    
    def analyze_cfn_failure(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        CloudFormationスタックの失敗を分析
        
        Args:
            input_data: 入力データ
            
        Returns:
            分析結果
        """
        stack_id = input_data.get('stackId', '')
        stack_name = input_data.get('stackName', '')
        logical_resource_id = input_data.get('logicalResourceId', '')
        resource_type = input_data.get('resourceType', '')
        status_reason = input_data.get('statusReason', '')
        template_info = input_data.get('templateInfo', {})
        failure_events = input_data.get('failureEvents', [])
        project_id = input_data.get('project_id', stack_id)
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not stack_id:
            raise ValueError("Stack ID is required")
        
        if not stack_name:
            raise ValueError("Stack Name is required")
        
        # 失敗情報を構築
        failure_info = f"Stack Name: {stack_name}\n"
        failure_info += f"Stack ID: {stack_id}\n"
        
        if logical_resource_id:
            failure_info += f"Failed Resource: {logical_resource_id} ({resource_type})\n"
        
        if status_reason:
            failure_info += f"Failure Reason: {status_reason}\n\n"
        
        # 詳細な失敗イベント情報を追加
        if failure_events:
            failure_info += "Detailed Failure Events:\n"
            for i, event in enumerate(failure_events):
                failure_info += f"Event {i+1}:\n"
                failure_info += f"  Resource: {event.get('logicalResourceId')} ({event.get('resourceType')})\n"
                failure_info += f"  Reason: {event.get('statusReason')}\n"
                failure_info += f"  Time: {event.get('timestamp')}\n\n"
        
        # テンプレート情報を追加（あれば）
        template_body = template_info.get('templateBody', {})
        if template_body:
            # テンプレートが大きすぎる場合は省略
            template_str = json.dumps(template_body, indent=2)
            if len(template_str) > 5000:
                template_str = template_str[:5000] + "...(truncated)"
            failure_info += f"Template Excerpt:\n{template_str}\n\n"
        
        # LLMに失敗分析を依頼
        messages = [
            {"role": "system", "content": """You are a cloud architect specializing in AWS CloudFormation troubleshooting. 
Analyze the provided CloudFormation stack failure and provide:

1. Root cause analysis of the failure
2. Specific recommendations to fix the issue
3. Best practices to prevent similar issues in the future
4. If applicable, alternative approaches to achieve the same goal

Format your response as a structured analysis report with clear sections."""},
            {"role": "user", "content": f"Analyze the following CloudFormation stack failure:\n\n{failure_info}"}
        ]
        
        response = self.ask_llm(messages)
        
        # 結果を保存
        analysis = response.get('content', '')
        analysis_id = str(uuid.uuid4())
        
        # スケーラブルなS3パス構造を使用
        artifact_data = self.artifacts.upload_artifact(
            data={
                "stack_id": stack_id,
                "stack_name": stack_name,
                "logical_resource_id": logical_resource_id,
                "resource_type": resource_type,
                "status_reason": status_reason,
                "failure_events": failure_events,
                "analysis": analysis,
                "created_at": timestamp
            },
            project_id=project_id,
            agent_type="cloud_architect",
            artifact_type="cfn_failure_analysis",
            artifact_id=analysis_id,
            timestamp=timestamp
        )
        
        s3_key = artifact_data["s3_key"]
        
        # 状態を更新
        self.add_to_memory({
            "type": "cfn_failure_analysis",
            "id": analysis_id,
            "stack_id": stack_id,
            "stack_name": stack_name,
            "s3_key": s3_key,
            "timestamp": timestamp
        })
        self.state = "cfn_failure_analyzed"
        self.save_state()
        
        # イベントを発行
        self.emit_event(
            detail_type="CfnFailureAnalysisCompleted",
            detail={
                "stack_id": stack_id,
                "stack_name": stack_name,
                "analysis_id": analysis_id,
                "s3_key": s3_key
            }
        )
        
        return {
            "status": "success",
            "stack_id": stack_id,
            "stack_name": stack_name,
            "analysis_id": analysis_id,
            "analysis": analysis,
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
                'design_cloud_architecture': 'design_cloud_architecture',
                'evaluate_architecture': 'evaluate_architecture',
                'create_infrastructure_diagram': 'create_infrastructure_diagram',
                'optimize_cost': 'optimize_cost',
                'design_disaster_recovery': 'design_disaster_recovery',
                'analyze_cfn_failure': 'analyze_cfn_failure',
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
            
            # クラウドアーキテクトエージェントを初期化
            cloud_architect = CloudArchitect(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                cloud_architect.load_state()
            
            # 入力データを処理
            result = cloud_architect.process(input_data)
            
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
            
            # クラウドアーキテクトエージェントを初期化
            cloud_architect = CloudArchitect(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                cloud_architect.load_state()
            
            # 入力データを処理
            result = cloud_architect.process(event)
            
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
    