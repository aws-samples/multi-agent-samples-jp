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

class PropertyTargetAgent(Agent):
    """特性目標設定エージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="property_target",
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
        process_type = input_data.get('process_type', 'set_target_properties')
        
        try:
            if process_type == 'set_target_properties':
                return self.set_target_properties(input_data)
            elif process_type == 'analyze_tradeoffs':
                return self.analyze_tradeoffs(input_data)
            elif process_type == 'validate_targets':
                return self.validate_targets(input_data)
            else:
                raise ValueError(f"Unknown process type: {process_type}")
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def set_target_properties(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        目標特性を設定
        
        Args:
            input_data: 入力データ
            
        Returns:
            設定された目標特性
        """
        requirements = input_data.get('requirements', '')
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        user_id = input_data.get('user_id', 'default_user')
        
        if not requirements:
            raise ValueError("Requirements are required")
        
        try:
            # LLMに目標特性設定を依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に材料特性の設定と分析に特化しています。あなたの役割は、ユーザーの要件に基づいて半導体材料の目標特性を科学的に定義することです。

# 専門知識
- 半導体物理学（バンドギャップ理論、キャリア輸送現象、光学特性など）
- 材料科学（結晶構造、欠陥物理、界面現象など）
- 量子力学（電子状態計算、バンド構造など）
- 熱力学（相安定性、形成エネルギーなど）
- 実験手法（特性評価技術、合成手法の制約など）

# 出力形式
各特性について以下の情報を含む構造化データを提供してください：
1. 目標値：科学的根拠に基づいた具体的な数値
2. 許容範囲：実用的な観点から許容される最小値と最大値
3. 単位：適切な物理単位（例：eV、cm²/Vs、W/mK）
4. 優先度：high/medium/low（トレードオフが必要な場合の判断基準）
5. 科学的根拠：なぜこの値が適切なのか、物理的・化学的な根拠
6. 測定手法：この特性を評価するための推奨測定技術

# 考慮すべき主要特性
- バンドギャップ：光吸収・発光特性、キャリア生成に関連
- キャリア移動度：電荷輸送効率、デバイス速度に関連
- キャリア濃度：導電性、ドーピング効率に関連
- 熱伝導率：熱管理、デバイス安定性に関連
- 光吸収係数：光電変換効率、光検出感度に関連
- 誘電率：電界効果、キャパシタンスに関連
- 機械的特性：耐久性、柔軟性、集積可能性に関連
- 化学的安定性：寿命、環境耐性に関連

# 制約条件の考慮
- コスト：高価な元素や複雑なプロセスの必要性
- 毒性：有害元素の使用制限
- 希少元素：入手困難な元素への依存度
- 環境負荷：製造・廃棄時の環境影響
- 合成可能性：現実的な製造技術での実現性

特性間のトレードオフを明示し、用途に応じた最適なバランスを提案してください。物理法則に反する非現実的な特性の組み合わせは避け、科学的に実現可能な目標を設定してください。
                """},
                {"role": "user", "content": f"""
以下の要件に基づいて、半導体材料の目標特性を詳細に定義してください。各特性について、目標値、許容範囲、単位、優先度、科学的根拠、および推奨測定手法を含めてください。

要件:
{requirements}

特に以下の点を考慮してください：
1. 用途に最適な特性値とその科学的根拠
2. 特性間の物理的・化学的なトレードオフ関係
3. 実現可能性の高い特性範囲
4. 材料合成と特性評価の実用的な制約
5. コスト、毒性、希少元素の使用などの実用的な制約条件

JSON形式で構造化された特性セットと、それに続く詳細な科学的説明を提供してください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を解析
            target_properties = self._parse_target_properties(response.get('content', ''))
            
            # 結果を保存
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "requirements": requirements, 
                    "target_properties": target_properties,
                    "user_id": user_id,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="property_target",
                artifact_type="target_properties",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "target_properties",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "requirements": requirements,
            #     "timestamp": timestamp
            # })
            # self.state = "target_properties_set"
            # self.save_state()
            
            # イベントを発行
            self.emit_event(
                detail_type="TargetPropertiesSet",
                detail={
                    "session_id": session_id,
                    "requirements": requirements,
                    "s3_key": s3_key
                }
            )
            
            return {
                "status": "success",
                "session_id": session_id,
                "target_properties": target_properties,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in set_target_properties: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def analyze_tradeoffs(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        特性間のトレードオフを分析
        
        Args:
            input_data: 入力データ
            
        Returns:
            トレードオフ分析結果
        """
        target_properties = input_data.get('target_properties', {})
        priority_feature = input_data.get('priority_feature', '')
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not target_properties:
            raise ValueError("Target properties are required")
        
        try:
            # LLMにトレードオフ分析を依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に材料特性間のトレードオフ分析に特化しています。あなたの役割は、半導体材料の異なる特性間の物理的・化学的な相互関係を分析し、最適なバランスを科学的根拠に基づいて提案することです。

# 専門知識
- 半導体物理学（バンドギャップ理論、キャリア輸送現象、光学特性など）
- 材料科学（結晶構造、欠陥物理、界面現象など）
- 量子力学（電子状態計算、バンド構造など）
- 熱力学（相安定性、形成エネルギーなど）
- 多目的最適化（パレート最適性、トレードオフ曲線など）

# 分析すべきトレードオフの例
1. バンドギャップと光吸収効率：
   - バンドギャップを広げると可視光領域の光吸収効率が低下
   - 理論的根拠：E_photon > E_gap の光子のみが吸収される

2. キャリア移動度と濃度：
   - 高濃度ドーピングによりキャリア濃度は増加するが、イオン化不純物散乱により移動度が低下
   - 理論的根拠：Brooks-Herring散乱モデル

3. 熱伝導率と電気伝導率：
   - 金属的材料では両者は比例関係（Wiedemann-Franz則）
   - 半導体では格子振動（フォノン）による熱伝導が支配的

4. 安定性と反応性：
   - 化学的に安定な材料は一般的に反応性が低く、センサーや触媒としての性能が制限される
   - 理論的根拠：結合エネルギーと表面エネルギーのトレードオフ

5. 機械的強度と柔軟性：
   - 硬い材料は一般的に脆く、柔軟性に欠ける
   - 理論的根拠：結合強度と結晶構造の関係

# 出力形式
1. トレードオフマトリックス：主要特性間の相互影響を定量的に評価（-2:強い負の相関、-1:弱い負の相関、0:無相関、+1:弱い正の相関、+2:強い正の相関）
2. 重要なトレードオフ関係の詳細分析：物理的・化学的メカニズム、数学的モデル、理論的限界
3. 最適化戦略：用途に応じた最適なバランスポイントの提案と科学的根拠
4. 材料設計への示唆：トレードオフを克服または緩和するための材料設計アプローチ（ドーピング、ナノ構造化、ヘテロ構造など）

科学的に正確で、定量的な分析を提供してください。理論モデル、実験データ、または計算結果に基づいた具体的な数値関係を示し、単なる定性的な説明は避けてください。
                """},
                {"role": "user", "content": f"""
以下の目標特性セットについて、詳細なトレードオフ分析を行ってください：

目標特性:
{json.dumps(target_properties, indent=2)}

優先特性: {priority_feature}

特に以下の点を分析してください：
1. 各特性ペア間の物理的・化学的な相互関係とトレードオフ
2. 優先特性を最大化する場合の他の特性への影響
3. 理論的に達成可能な特性の組み合わせの限界
4. 特性間のトレードオフを緩和するための材料設計戦略
5. 用途に最適な特性バランスの科学的根拠に基づく推奨

トレードオフマトリックス、詳細な物理的メカニズムの説明、定量的な関係式、および最適化戦略を含む包括的な分析を提供してください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を保存
            tradeoff_analysis = response.get('content', '')
            
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "target_properties": target_properties, 
                    "priority_feature": priority_feature,
                    "tradeoff_analysis": tradeoff_analysis,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="property_target",
                artifact_type="tradeoff_analysis",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "tradeoff_analysis",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "tradeoffs_analyzed"
            # self.save_state()
            
            return {
                "status": "success",
                "session_id": session_id,
                "tradeoff_analysis": tradeoff_analysis,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in analyze_tradeoffs: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def validate_targets(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        目標特性の実現可能性を検証
        
        Args:
            input_data: 入力データ
            
        Returns:
            検証結果
        """
        target_properties = input_data.get('target_properties', {})
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not target_properties:
            raise ValueError("Target properties are required")
        
        try:
            # LLMに目標特性の検証を依頼
            messages = [
                {"role": "system", "content": "You are a materials science expert specializing in semiconductor materials. Your task is to validate whether the target properties are physically and chemically feasible, and suggest adjustments if needed."},
                {"role": "user", "content": f"Validate the feasibility of the following target properties for semiconductor materials:\n\n{json.dumps(target_properties, indent=2)}"}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を保存
            validation_result = response.get('content', '')
            
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "target_properties": target_properties, 
                    "validation_result": validation_result,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="property_target",
                artifact_type="validation_result",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "validation_result",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "targets_validated"
            # self.save_state()
            
            return {
                "status": "success",
                "session_id": session_id,
                "validation_result": validation_result,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in validate_targets: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_target_properties(self, llm_response: str) -> Dict[str, Any]:
        """
        LLMの応答から目標特性を解析
        
        Args:
            llm_response: LLMの応答テキスト
            
        Returns:
            解析された目標特性
        """
        # 実際の実装では、LLMの応答を構造化データに変換するロジックを実装
        # このサンプルでは、モック応答を返す
        return {
            'bandgap': {
                'value': 1.5,
                'unit': 'eV',
                'range': [1.3, 1.7],
                'priority': 'high'
            },
            'carrier_mobility': {
                'value': 1000,
                'unit': 'cm²/Vs',
                'range': [800, 1200],
                'priority': 'medium'
            },
            'thermal_conductivity': {
                'value': 50,
                'unit': 'W/mK',
                'range': [40, 60],
                'priority': 'low'
            },
            'constraints': {
                'toxicity': 'low',
                'cost': 'medium',
                'rare_elements': 'avoid'
            }
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
                'set_target_properties': 'set_target_properties',
                'analyze_tradeoffs': 'analyze_tradeoffs',
                'validate_targets': 'validate_targets',
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
            
            # 特性目標設定エージェントを初期化
            property_target = PropertyTargetAgent(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                property_target.load_state()
            
            # 入力データを処理
            result = property_target.process(input_data)
            
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
            
            # 特性目標設定エージェントを初期化
            property_target = PropertyTargetAgent(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                property_target.load_state()
            
            # 入力データを処理
            result = property_target.process(event)
            
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
