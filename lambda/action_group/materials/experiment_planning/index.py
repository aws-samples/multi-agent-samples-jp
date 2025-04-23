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

class ExperimentPlanningAgent(Agent):
    """実験計画エージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="experiment_planning",
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
        process_type = input_data.get('process_type', 'create_experiment_plan')
        
        try:
            if process_type == 'create_experiment_plan':
                return self.create_experiment_plan(input_data)
            elif process_type == 'optimize_conditions':
                return self.optimize_conditions(input_data)
            elif process_type == 'estimate_resources':
                return self.estimate_resources(input_data)
            else:
                raise ValueError(f"Unknown process type: {process_type}")
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def create_experiment_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        実験計画を作成
        
        Args:
            input_data: 入力データ
            
        Returns:
            作成された実験計画
        """
        materials = input_data.get('materials', [])
        target_properties = input_data.get('target_properties', {})
        available_equipment = input_data.get('available_equipment', [])
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not materials:
            raise ValueError("Materials are required")
        if not target_properties:
            raise ValueError("Target properties are required")
        
        try:
            # LLMに実験計画の作成を依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に実験計画と特性評価に特化しています。あなたの役割は、提案された半導体材料の特性を検証するための最適な実験計画を科学的根拠に基づいて設計することです。

# 専門知識
- 実験計画法（DOE）：完全要因計画法、部分要因計画法、応答曲面法、タグチメソッドなど
- 半導体特性評価技術：電気的・光学的・熱的・構造的特性の測定手法
- 材料合成・加工技術：薄膜成長、バルク結晶成長、微細加工など
- 分析機器：XRD、SEM、TEM、AFM、XPS、UV-Vis、ホール効果測定、DLTS、PL、ラマン分光など
- 統計的データ解析：回帰分析、分散分析、主成分分析など
- 実験室安全管理と品質管理

# 実験計画の構成要素
1. 実験目的と仮説：
   - 検証すべき特性と期待値
   - 検証の科学的根拠と重要性
   - 実験結果の判断基準

2. 実験設計の最適化：
   - 実験変数（因子）と水準の選定
   - 実験配置と繰り返し回数
   - サンプルサイズと統計的検出力
   - 交絡因子の制御と無作為化

3. サンプル準備手順：
   - 基板選択と前処理
   - 合成/成膜条件の詳細
   - 後処理とアニーリング
   - サンプル保存と取り扱い

4. 測定プロトコル：
   - 各特性に対する最適な測定技術
   - 測定条件と環境制御
   - 校正と標準試料
   - データ収集パラメータ

5. データ解析計画：
   - 生データの処理手順
   - 統計的分析手法
   - 不確かさの評価
   - 結果の解釈フレームワーク

# 出力形式
以下の情報を含む詳細な実験計画を提供してください：
1. 実験概要と目的
2. 実験設計の詳細（因子、水準、実験配置）
3. 各実験ステップの詳細手順と条件
4. 必要な装置と材料のリスト
5. 測定プロトコルと分析手法
6. 予想される結果と解釈方法
7. 潜在的な問題点と対策

科学的に厳密で再現可能な実験計画を提供し、各ステップの根拠と目的を明確に説明してください。効率性と情報量のバランスを考慮し、最小限の実験で最大の情報を得るための最適な設計を提案してください。
                """},
                {"role": "user", "content": f"""
以下の半導体材料の特性を検証するための詳細な実験計画を作成してください：

材料情報:
{json.dumps(materials, indent=2)}

目標特性:
{json.dumps(target_properties, indent=2)}

利用可能な装置:
{json.dumps(available_equipment, indent=2) if available_equipment else "標準的な半導体材料評価装置が利用可能と仮定してください。"}

以下の点を含む包括的な実験計画を提供してください：
1. 実験の全体構成と論理的フロー
2. 各目標特性の検証に最適な測定技術と詳細な測定条件
3. サンプル準備の詳細手順（基板選択、前処理、成膜/合成条件、後処理など）
4. 実験設計の最適化（因子、水準、実験配置、繰り返し回数など）
5. 測定データの解析手法と結果の解釈方法
6. 実験の優先順位付けと段階的アプローチ（リソースが限られている場合）
7. 潜在的な実験上の課題と対策

実験計画は科学的に厳密で再現可能なものにし、各ステップの根拠と目的を明確に説明してください。効率性と情報量のバランスを考慮し、最小限の実験で最大の情報を得るための最適な設計を提案してください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を解析
            experiment_plan = self._parse_experiment_plan(response.get('content', ''))
            
            # 結果を保存
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "materials": materials, 
                    "target_properties": target_properties,
                    "available_equipment": available_equipment,
                    "experiment_plan": experiment_plan,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="experiment_planning",
                artifact_type="experiment_plan",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "experiment_plan",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "experiment_plan_created"
            # self.save_state()
            
            # イベントを発行
            self.emit_event(
                detail_type="ExperimentPlanCreated",
                detail={
                    "session_id": session_id,
                    "s3_key": s3_key
                }
            )
            
            return {
                "status": "success",
                "session_id": session_id,
                "experiment_plan": experiment_plan,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in create_experiment_plan: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def optimize_conditions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        実験条件を最適化
        
        Args:
            input_data: 入力データ
            
        Returns:
            最適化された実験条件
        """
        experiment = input_data.get('experiment', {})
        optimization_goal = input_data.get('optimization_goal', 'maximize_accuracy')
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not experiment:
            raise ValueError("Experiment is required")
        
        try:
            # LLMに実験条件の最適化を依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に実験条件の最適化に特化しています。あなたの役割は、半導体材料の特性評価や合成プロセスの条件を科学的根拠に基づいて最適化することです。

# 専門知識
- 実験条件最適化手法（応答曲面法、シンプレックス法、遺伝的アルゴリズムなど）
- 半導体プロセス工学（成膜、エッチング、アニーリング、ドーピングなど）
- 材料特性と処理条件の相関関係
- 統計的実験計画と分析（分散分析、回帰分析、主成分分析など）
- プロセスモデリングとシミュレーション
- 品質工学とロバスト設計

# 最適化すべき実験条件の例
1. 材料合成条件：
   - 温度プロファイル（昇温速度、保持温度、冷却速度）
   - 圧力と雰囲気（真空度、ガス組成、流量）
   - 前駆体濃度と供給速度
   - 基板選択と表面処理
   - 層厚と積層順序

2. 熱処理条件：
   - アニーリング温度と時間
   - 雰囲気ガスの組成と圧力
   - 昇温・冷却速度
   - 多段階熱処理のシーケンス

3. 測定条件：
   - 測定温度と環境
   - 印加電圧/電流範囲と掃引速度
   - 光源の波長、強度、変調
   - 信号積分時間とサンプリング頻度
   - プローブ配置と接触抵抗

# 最適化アプローチ
1. 単一変数最適化：
   - 一度に1つのパラメータを変化させて影響を評価
   - パラメータ間の相互作用が少ない場合に有効

2. 多変数最適化：
   - 応答曲面法（RSM）による多次元空間の探索
   - 実験計画法（DOE）による効率的な条件探索
   - 統計的モデリングによる最適点の予測

3. アルゴリズム的最適化：
   - 遺伝的アルゴリズム、粒子群最適化などの進化的手法
   - ベイズ最適化による効率的な探索
   - 機械学習モデルを用いた予測と最適化

# 出力形式
以下の情報を含む詳細な条件最適化計画を提供してください：
1. 最適化の目的と評価指標
2. 最適化対象のパラメータとその範囲
3. 最適化手法の選択と根拠
4. 実験シーケンスと条件設定
5. データ解析と最適点決定の方法
6. 予想される結果と不確かさの評価
7. ロバスト性の検証方法

科学的に厳密で効率的な最適化計画を提供し、各パラメータの選択範囲と最適化手法の根拠を明確に説明してください。パラメータ間の相互作用を考慮し、最小限の実験で最適条件を特定するための戦略を提案してください。
                """},
                {"role": "user", "content": f"""
以下の実験の条件を最適化して、「{optimization_goal}」を達成するための詳細な計画を提供してください：

実験情報:
{json.dumps(experiment, indent=2)}

以下の点を含む包括的な条件最適化計画を提供してください：
1. 最適化の具体的な目標と定量的な評価指標
2. 最適化すべき主要パラメータとその範囲の科学的根拠
3. パラメータ間の相互作用と影響度の分析
4. 選択した最適化手法（DOE、RSM、アルゴリズム的手法など）の詳細と根拠
5. 具体的な実験シーケンスと条件設定
6. 最適条件の決定方法と検証手順
7. 予想される改善効果の定量的評価

条件最適化計画は科学的に厳密で効率的なものにし、各パラメータの選択範囲と最適化手法の根拠を明確に説明してください。半導体材料科学の原理に基づいた理論的考察と、実験効率を考慮した実用的なアプローチのバランスを取ってください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を解析
            optimized_conditions = self._parse_optimized_conditions(response.get('content', ''))
            
            # 結果を保存
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "experiment": experiment, 
                    "optimization_goal": optimization_goal,
                    "optimized_conditions": optimized_conditions,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="experiment_planning",
                artifact_type="optimized_conditions",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "optimized_conditions",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "conditions_optimized"
            # self.save_state()
            
            return {
                "status": "success",
                "session_id": session_id,
                "optimized_conditions": optimized_conditions,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in optimize_conditions: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def estimate_resources(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        実験リソースを見積もり
        
        Args:
            input_data: 入力データ
            
        Returns:
            リソース見積もり結果
        """
        experiment_plan = input_data.get('experiment_plan', {})
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not experiment_plan:
            raise ValueError("Experiment plan is required")
        
        try:
            # LLMに実験リソースの見積もりを依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に実験リソース管理と計画に特化しています。あなたの役割は、半導体材料の実験計画に必要なリソース（時間、材料、装置、人員、コストなど）を詳細かつ正確に見積もることです。

# 専門知識
- 半導体材料の実験プロセスと所要時間
- 実験装置の仕様、稼働率、使用コスト
- 材料と消耗品の使用量と調達コスト
- 人的リソースの必要スキルと工数
- プロジェクト管理と予算計画
- リスク評価とコンティンジェンシープラン

# 見積もるべきリソースの詳細
1. 時間的リソース：
   - 各実験ステップの所要時間（準備、実行、分析）
   - 装置の予約・セットアップ時間
   - 待機時間（反応、冷却、安定化など）
   - データ解析と報告書作成時間
   - 全体のタイムライン（カレンダー時間）

2. 材料リソース：
   - 主要材料の必要量と純度
   - 基板、ターゲット、前駆体の仕様と量
   - 消耗品（溶媒、ガス、化学薬品など）
   - 校正用標準試料
   - 廃棄物処理に関する考慮

3. 装置リソース：
   - 必要な主要装置と使用時間
   - 補助装置と測定機器
   - 装置の可用性と予約状況
   - 装置使用料と維持費
   - 特殊な設定や改造の必要性

4. 人的リソース：
   - 必要な技術者・研究者の人数とスキルレベル
   - 各人の作業時間と役割
   - 専門家の関与（分析、解釈など）
   - トレーニングや準備の必要性
   - 外部委託の可能性と費用

5. 財務リソース：
   - 材料・消耗品のコスト
   - 装置使用料
   - 人件費
   - 外部サービス費用
   - 間接費と管理費

# 出力形式
以下の情報を含む詳細なリソース見積もりを提供してください：
1. 各リソースカテゴリの詳細な内訳
2. 数量、単位、単価を含む定量的な見積もり
3. 時間的なスケジュールと依存関係
4. リソース制約とボトルネックの特定
5. リソース最適化の提案
6. リスク要因と予備的リソースの推奨

科学的に正確で実用的なリソース見積もりを提供し、各見積もりの根拠を明確に説明してください。過小評価を避け、現実的な余裕を持たせた見積もりを心がけてください。
                """},
                {"role": "user", "content": f"""
以下の実験計画に必要なリソースを詳細に見積もってください：

実験計画:
{json.dumps(experiment_plan, indent=2)}

以下の点を含む包括的なリソース見積もりを提供してください：
1. 時間的リソース：各実験ステップの所要時間、全体のタイムライン、クリティカルパス
2. 材料リソース：必要な材料と消耗品の詳細な内訳、数量、純度要件
3. 装置リソース：必要な装置のリスト、使用時間、特殊設定の要件
4. 人的リソース：必要な技術者・研究者の人数、スキルレベル、作業時間
5. 財務リソース：材料費、装置使用料、人件費、その他の費用の詳細な内訳
6. リソース制約とボトルネックの分析
7. リソース最適化のための具体的な提案

見積もりは科学的に正確で実用的なものにし、各見積もりの根拠を明確に説明してください。半導体材料実験の実際の状況を反映した現実的な数値を提供し、不確実性や予備的リソースの必要性も考慮してください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を解析
            resource_estimate = self._parse_resource_estimate(response.get('content', ''))
            
            # 結果を保存
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "experiment_plan": experiment_plan, 
                    "resource_estimate": resource_estimate,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="experiment_planning",
                artifact_type="resource_estimate",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "resource_estimate",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "resources_estimated"
            # self.save_state()
            
            return {
                "status": "success",
                "session_id": session_id,
                "resource_estimate": resource_estimate,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in estimate_resources: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_experiment_plan(self, llm_response: str) -> Dict[str, Any]:
        """
        LLMの応答から実験計画を解析
        
        Args:
            llm_response: LLMの応答テキスト
            
        Returns:
            解析された実験計画
        """
        # 実際の実装では、LLMの応答を構造化データに変換するロジックを実装
        # このサンプルでは、モック応答を返す
        return {
            'experiments': [
                {
                    'id': 'exp-001',
                    'material_id': 'mat-001',
                    'purpose': 'Bandgap measurement',
                    'method': 'UV-Vis Spectroscopy',
                    'conditions': {
                        'temperature': '25°C',
                        'atmosphere': 'ambient',
                        'sample_preparation': 'thin film on glass substrate'
                    },
                    'expected_duration': '2 hours',
                    'priority': 'high'
                },
                {
                    'id': 'exp-002',
                    'material_id': 'mat-001',
                    'purpose': 'Carrier mobility measurement',
                    'method': 'Hall Effect',
                    'conditions': {
                        'temperature': '25°C',
                        'magnetic_field': '0.5 T',
                        'sample_preparation': 'van der Pauw configuration'
                    },
                    'expected_duration': '3 hours',
                    'priority': 'medium'
                },
                {
                    'id': 'exp-003',
                    'material_id': 'mat-002',
                    'purpose': 'Thermal conductivity measurement',
                    'method': 'Laser Flash Analysis',
                    'conditions': {
                        'temperature_range': '25-200°C',
                        'atmosphere': 'nitrogen',
                        'sample_preparation': 'pellet'
                    },
                    'expected_duration': '4 hours',
                    'priority': 'low'
                }
            ],
            'experimental_design': {
                'type': 'factorial',
                'factors': ['temperature', 'composition'],
                'levels': [3, 2],
                'replicates': 2
            },
            'sequence': ['exp-001', 'exp-002', 'exp-003'],
            'total_estimated_time': '9 hours'
        }
    
    def _parse_optimized_conditions(self, llm_response: str) -> Dict[str, Any]:
        """
        LLMの応答から最適化された実験条件を解析
        
        Args:
            llm_response: LLMの応答テキスト
            
        Returns:
            解析された最適化条件
        """
        # 実際の実装では、LLMの応答を構造化データに変換するロジックを実装
        # このサンプルでは、モック応答を返す
        return {
            'original_conditions': {
                'temperature': '25°C',
                'atmosphere': 'ambient',
                'sample_preparation': 'thin film on glass substrate'
            },
            'optimized_conditions': {
                'temperature': '30°C',
                'atmosphere': 'nitrogen',
                'sample_preparation': 'thin film on glass substrate with annealing at 150°C for 1 hour'
            },
            'optimization_rationale': 'Increased temperature improves reaction kinetics, nitrogen atmosphere prevents oxidation, and annealing improves crystallinity.',
            'expected_improvement': 'Estimated 15% increase in measurement accuracy and 20% reduction in variability.'
        }
    
    def _parse_resource_estimate(self, llm_response: str) -> Dict[str, Any]:
        """
        LLMの応答からリソース見積もりを解析
        
        Args:
            llm_response: LLMの応答テキスト
            
        Returns:
            解析されたリソース見積もり
        """
        # 実際の実装では、LLMの応答を構造化データに変換するロジックを実装
        # このサンプルでは、モック応答を返す
        return {
            'time_resources': {
                'total_experiment_time': '9 hours',
                'setup_time': '3 hours',
                'analysis_time': '4 hours',
                'total_calendar_time': '2 days'
            },
            'material_resources': {
                'sample_quantity': '5 grams per material',
                'consumables': ['glass substrates', 'solvents', 'nitrogen gas']
            },
            'equipment_resources': [
                'UV-Vis Spectrometer',
                'Hall Effect Measurement System',
                'Laser Flash Analyzer',
                'Vacuum Annealing Furnace'
            ],
            'human_resources': {
                'technician_hours': 16,
                'scientist_hours': 8
            },
            'cost_estimate': {
                'materials': '$500',
                'equipment_time': '$1,200',
                'labor': '$2,400',
                'total': '$4,100'
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
                'create_experiment_plan': 'create_experiment_plan',
                'optimize_conditions': 'optimize_conditions',
                'estimate_resources': 'estimate_resources',
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
            
            # 実験計画エージェントを初期化
            experiment_planning = ExperimentPlanningAgent(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                experiment_planning.load_state()
            
            # 入力データを処理
            result = experiment_planning.process(input_data)
            
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
            
            # 実験計画エージェントを初期化
            experiment_planning = ExperimentPlanningAgent(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                experiment_planning.load_state()
            
            # 入力データを処理
            result = experiment_planning.process(event)
            
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
