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

class InverseDesignAgent(Agent):
    """材料逆設計エージェント"""
    
    def __init__(self, agent_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="inverse_design",
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
        process_type = input_data.get('process_type', 'design_materials')
        
        try:
            if process_type == 'design_materials':
                return self.design_materials(input_data)
            elif process_type == 'rank_candidates':
                return self.rank_candidates(input_data)
            elif process_type == 'evaluate_feasibility':
                return self.evaluate_feasibility(input_data)
            else:
                raise ValueError(f"Unknown process type: {process_type}")
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def design_materials(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        目標特性に基づいて材料を設計
        
        Args:
            input_data: 入力データ
            
        Returns:
            設計された候補材料
        """
        target_properties = input_data.get('target_properties', {})
        constraints = input_data.get('constraints', {})
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not target_properties:
            raise ValueError("Target properties are required")
        
        try:
            # LLMに材料設計を依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に材料の逆設計に特化しています。あなたの役割は、指定された目標特性を実現する最適な材料組成と構造を設計することです。

# 専門知識
- 計算材料科学（第一原理計算、分子動力学シミュレーション、機械学習モデルなど）
- 材料データベース（Materials Project、AFLOW、OQMD、Citrine、MolSSIなど）
- 結晶化学（結晶構造、点欠陥、表面・界面現象など）
- 半導体物理（バンド構造、キャリア輸送、光学特性など）
- 材料合成手法（薄膜成長技術、バルク結晶成長、ナノ材料合成など）

# 設計アプローチ
1. 材料スクリーニング：
   - 既知の材料データベースから目標特性に近い候補を特定
   - 材料ゲノムイニシアチブのデータと手法の活用
   - 高スループットスクリーニング手法の適用

2. 組成最適化：
   - 元素置換と固溶体形成による特性調整
   - ドーピング戦略（n型、p型、補償ドーピングなど）
   - 組成勾配と多元系合金の設計

3. 構造設計：
   - 結晶構造の選択と最適化
   - 欠陥エンジニアリング（空孔、格子間原子、アンチサイト欠陥など）
   - ナノ構造化（量子井戸、超格子、ナノ粒子など）
   - ヘテロ構造と界面設計

4. 特性予測：
   - 第一原理計算に基づく電子状態と物性予測
   - 半経験的モデルによる特性推定
   - 機械学習モデルを用いた特性予測

# 出力形式
各候補材料について以下の情報を含む詳細な設計を提供してください：
1. 化学組成：元素と化学量論比
2. 結晶構造：空間群、格子定数、原子位置
3. 電子構造：バンドギャップ、バンド構造の特徴
4. 予測される物性値：目標特性に対応する定量的な予測値
5. 合成方法の提案：最適な合成手法と条件
6. 信頼性評価：予測の確信度と不確実性の範囲
7. 制約条件への適合性：コスト、毒性、希少元素使用などの評価

科学的に正確で実現可能な材料設計を提供し、予測の根拠となる理論モデルや計算手法を明示してください。複数の候補材料を提案し、それぞれの長所と短所を比較してください。
                """},
                {"role": "user", "content": f"""
以下の目標特性を実現するための最適な半導体材料を設計してください：

目標特性:
{json.dumps(target_properties, indent=2)}

制約条件:
{json.dumps(constraints, indent=2)}

以下の点を考慮した詳細な材料設計を提供してください：
1. 化学組成と結晶構造の詳細（元素選択の根拠を含む）
2. 各目標特性をどのように実現するか、その物理的・化学的メカニズム
3. 予測される特性値と目標値との比較
4. 合成可能性と推奨される合成手法
5. 制約条件（コスト、毒性、希少元素使用など）への適合性
6. 複数の候補材料とそれらの比較評価

各候補材料について、組成、構造、予測特性、合成方法、制約条件への適合性を含む包括的な情報を提供してください。予測の科学的根拠と信頼性も明示してください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を解析
            candidate_materials = self._parse_candidate_materials(response.get('content', ''))
            
            # 結果を保存
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "target_properties": target_properties, 
                    "constraints": constraints,
                    "candidate_materials": candidate_materials,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="inverse_design",
                artifact_type="candidate_materials",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "candidate_materials",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "materials_designed"
            # self.save_state()
            
            # イベントを発行
            self.emit_event(
                detail_type="MaterialsDesigned",
                detail={
                    "session_id": session_id,
                    "s3_key": s3_key
                }
            )
            
            return {
                "status": "success",
                "session_id": session_id,
                "candidate_materials": candidate_materials,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in design_materials: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def rank_candidates(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        候補材料をランク付け
        
        Args:
            input_data: 入力データ
            
        Returns:
            ランク付けされた候補材料
        """
        candidate_materials = input_data.get('candidate_materials', [])
        ranking_criteria = input_data.get('ranking_criteria', {})
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not candidate_materials:
            raise ValueError("Candidate materials are required")
        
        try:
            # LLMに候補材料のランク付けを依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に材料評価と選定に特化しています。あなたの役割は、候補材料を複数の評価基準に基づいて詳細に分析し、最適な選択肢を科学的根拠に基づいて推奨することです。

# 専門知識
- 多基準意思決定分析（MCDA）手法
- 材料性能評価と特性分析
- 半導体製造プロセスと量産性評価
- コスト分析と経済的実現可能性
- 環境影響評価とライフサイクル分析
- 信頼性工学と寿命予測

# 評価基準の詳細
1. 特性一致度（Property Match）：
   - 目標特性との定量的な一致度
   - 重み付き平均二乗偏差（WMSD）による評価
   - 各特性の重要度に応じた重み付け

2. 合成可能性（Synthesis Feasibility）：
   - 既知の合成手法との互換性
   - スケーラビリティと量産性
   - 再現性と歩留まり予測
   - 必要な装置と技術的複雑さ

3. コスト効率（Cost Efficiency）：
   - 原材料コスト（元素の市場価格に基づく）
   - 製造プロセスコスト（エネルギー、時間、装置償却）
   - スケールアップ時の経済性

4. 安定性と信頼性（Stability & Reliability）：
   - 熱力学的安定性（分解エネルギー、相安定性）
   - 環境安定性（酸化、湿度、光に対する耐性）
   - 長期信頼性と劣化メカニズム

5. 環境影響（Environmental Impact）：
   - 毒性元素の含有量と代替可能性
   - 製造時のエネルギー消費と排出物
   - リサイクル可能性と廃棄物管理

6. 革新性（Innovation Potential）：
   - 既存材料からの性能向上度
   - 特許性と知的財産の観点
   - 将来の改良可能性

# 出力形式
各候補材料について以下の情報を含む詳細な評価を提供してください：
1. 総合スコア（0-100）と順位
2. 各評価基準のスコア（0-10）と詳細な根拠
3. 長所と短所の分析
4. 改良のための具体的な提案
5. 用途に応じた推奨度

科学的に厳密で、定量的な評価を提供してください。主観的な判断は避け、具体的なデータと計算に基づいた分析を行ってください。評価基準間のトレードオフを明確に示し、最終的な推奨の根拠を詳細に説明してください。
                """},
                {"role": "user", "content": f"""
以下の候補材料を詳細に評価し、指定された基準に基づいてランク付けしてください：

候補材料:
{json.dumps(candidate_materials, indent=2)}

評価基準と重み付け:
{json.dumps(ranking_criteria, indent=2) if ranking_criteria else "特性一致度(0.4), 合成可能性(0.3), コスト効率(0.2), 安定性(0.1)"}

以下の点を含む詳細な評価とランキングを提供してください：
1. 各材料の各評価基準に対する定量的スコア（0-10）と詳細な根拠
2. 総合スコア（0-100）の計算と最終ランキング
3. 各材料の長所と短所の詳細分析
4. 各材料の改良可能性と具体的な提案
5. 最適な材料の選定理由と科学的根拠

評価は科学的に厳密で、定量的なデータに基づいたものにしてください。主観的判断ではなく、材料科学の原理と具体的な数値に基づいた分析を提供してください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を解析
            ranked_materials = self._parse_ranked_materials(response.get('content', ''), candidate_materials)
            
            # 結果を保存
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "candidate_materials": candidate_materials, 
                    "ranking_criteria": ranking_criteria,
                    "ranked_materials": ranked_materials,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="inverse_design",
                artifact_type="ranked_materials",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "ranked_materials",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "materials_ranked"
            # self.save_state()
            
            return {
                "status": "success",
                "session_id": session_id,
                "ranked_materials": ranked_materials,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in rank_candidates: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def evaluate_feasibility(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        材料の合成可能性を評価
        
        Args:
            input_data: 入力データ
            
        Returns:
            合成可能性評価結果
        """
        material = input_data.get('material', {})
        session_id = input_data.get('session_id', str(uuid.uuid4()))
        timestamp = input_data.get('timestamp', datetime.utcnow().isoformat())
        
        if not material:
            raise ValueError("Material is required")
        
        try:
            # LLMに材料の合成可能性評価を依頼
            messages = [
                {"role": "system", "content": """
あなたは半導体材料科学の専門家で、特に材料合成と製造プロセスに特化しています。あなたの役割は、提案された材料の合成可能性を詳細に評価し、最適な合成手法と条件を科学的根拠に基づいて提案することです。

# 専門知識
- 薄膜成長技術（PVD、CVD、ALD、MBE、スパッタリングなど）
- バルク結晶成長（チョクラルスキー法、ブリッジマン法、フラックス法など）
- ナノ材料合成（コロイド合成、水熱合成、ゾル-ゲル法など）
- 熱力学と相平衡（状態図、形成エネルギー、核形成理論など）
- 反応速度論（成長速度、活性化エネルギー、律速段階など）
- 材料特性評価（構造解析、組成分析、物性測定など）

# 評価すべき合成可能性の側面
1. 熱力学的安定性：
   - 形成エネルギーと相安定性
   - 分解温度と相転移点
   - 競合相の存在と相分離傾向
   - 状態図に基づく安定組成範囲

2. 合成プロセスの実現可能性：
   - 適切な前駆体と原料の入手可能性
   - 必要な温度、圧力、雰囲気条件の実現性
   - 反応経路と中間生成物の制御
   - スケールアップ時の課題と解決策

3. 構造制御の可能性：
   - 結晶構造と結晶性の制御方法
   - 欠陥密度と欠陥タイプの制御
   - 組成均一性の確保
   - 界面と表面の制御

4. 特性再現性：
   - プロセスパラメータと特性の相関
   - バッチ間変動の予測と制御
   - 特性評価の方法と精度
   - スケールアップ時の特性維持

# 出力形式
以下の情報を含む詳細な合成可能性評価を提供してください：
1. 総合的な合成可能性評価（高/中/低）と科学的根拠
2. 推奨される合成手法の詳細（原理、装置、プロセスフロー）
3. 最適な合成条件（温度、圧力、時間、雰囲気など）
4. 予想される課題と対策
5. 特性制御のための具体的な戦略
6. 品質評価のための推奨測定手法

科学的に厳密で実用的な評価を提供し、理論と実験の両面から合成可能性を検討してください。具体的な数値、反応式、プロセスパラメータを含め、実際に材料を合成するために必要な詳細情報を提供してください。
                """},
                {"role": "user", "content": f"""
以下の半導体材料の合成可能性を詳細に評価し、最適な合成手法と条件を提案してください：

材料情報:
{json.dumps(material, indent=2)}

以下の点を含む詳細な合成可能性評価を提供してください：
1. 熱力学的安定性の評価（形成エネルギー、相安定性、分解温度など）
2. 複数の合成手法の比較評価と最適手法の選定
3. 最適な合成条件の詳細（温度、圧力、時間、前駆体、雰囲気など）
4. 予想される合成上の課題と具体的な対策
5. 目標特性を実現するための構造・組成制御戦略
6. 合成された材料の品質評価方法

評価は科学的に厳密で、具体的な数値、反応式、プロセスパラメータを含む実用的なものにしてください。理論的な考察だけでなく、実験的な実現可能性も詳細に検討してください。
                """}
            ]
            
            response = self.ask_llm(messages)
            
            # 結果を保存
            feasibility_evaluation = response.get('content', '')
            
            artifact_data = self.artifacts.upload_artifact(
                data={
                    "session_id": session_id,
                    "material": material, 
                    "feasibility_evaluation": feasibility_evaluation,
                    "created_at": timestamp
                },
                project_id=session_id,
                agent_type="inverse_design",
                artifact_type="feasibility_evaluation",
                artifact_id=str(uuid.uuid4()),
                timestamp=timestamp
            )
            
            s3_key = artifact_data["s3_key"]
            
            # 状態を更新
            # self.add_to_memory({
            #     "type": "feasibility_evaluation",
            #     "session_id": session_id,
            #     "s3_key": s3_key,
            #     "timestamp": timestamp
            # })
            # self.state = "feasibility_evaluated"
            # self.save_state()
            
            return {
                "status": "success",
                "session_id": session_id,
                "feasibility_evaluation": feasibility_evaluation,
                "s3_key": s3_key
            }
        except Exception as e:
            logger.error(f"Error in evaluate_feasibility: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _parse_candidate_materials(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        LLMの応答から候補材料を解析
        
        Args:
            llm_response: LLMの応答テキスト
            
        Returns:
            解析された候補材料のリスト
        """
        # 実際の実装では、LLMの応答を構造化データに変換するロジックを実装
        # このサンプルでは、モック応答を返す
        return [
            {
                'id': 'mat-001',
                'composition': 'Cu(In,Ga)Se2',
                'structure': 'chalcopyrite',
                'predicted_properties': {
                    'bandgap': 1.4,
                    'carrier_mobility': 950,
                    'thermal_conductivity': 45
                },
                'confidence': 0.85
            },
            {
                'id': 'mat-002',
                'composition': 'CdTe',
                'structure': 'zinc blende',
                'predicted_properties': {
                    'bandgap': 1.5,
                    'carrier_mobility': 1100,
                    'thermal_conductivity': 52
                },
                'confidence': 0.78
            },
            {
                'id': 'mat-003',
                'composition': 'GaAs',
                'structure': 'zinc blende',
                'predicted_properties': {
                    'bandgap': 1.42,
                    'carrier_mobility': 8500,
                    'thermal_conductivity': 55
                },
                'confidence': 0.92
            }
        ]
    
    def _parse_ranked_materials(self, llm_response: str, candidate_materials: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        LLMの応答からランク付けされた材料を解析
        
        Args:
            llm_response: LLMの応答テキスト
            candidate_materials: 元の候補材料リスト
            
        Returns:
            ランク付けされた材料のリスト
        """
        # 実際の実装では、LLMの応答を構造化データに変換するロジックを実装
        # このサンプルでは、モック応答を返す
        ranked_materials = candidate_materials.copy()
        
        # ランク情報を追加
        for i, material in enumerate(ranked_materials):
            material['rank'] = i + 1
            material['rank_reason'] = f"Ranked #{i+1} due to balance of properties and feasibility"
        
        # ランク順にソート
        ranked_materials.sort(key=lambda x: x['rank'])
        
        return ranked_materials

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
                'design_materials': 'design_materials',
                'rank_candidates': 'rank_candidates',
                'evaluate_feasibility': 'evaluate_feasibility',
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
            
            # 材料逆設計エージェントを初期化
            inverse_design = InverseDesignAgent(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                inverse_design.load_state()
            
            # 入力データを処理
            result = inverse_design.process(input_data)
            
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
            
            # 材料逆設計エージェントを初期化
            inverse_design = InverseDesignAgent(agent_id)
            
            # 既存の状態を読み込み
            if agent_id:
                inverse_design.load_state()
            
            # 入力データを処理
            result = inverse_design.process(event)
            
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
