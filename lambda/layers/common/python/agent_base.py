"""
エージェントの基本クラス
"""
import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from agent_utils import DynamoDBClient, S3Client, SQSClient, EventBridgeClient
from llm_client import LLMClient

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Agent:
    """エージェントの基本クラス"""
    
    def __init__(self, 
                agent_id: str = None, 
                agent_type: str = "base",
                agent_state_table: str = None,
                message_history_table: str = None,
                artifacts_bucket: str = None,
                communication_queue_url: str = None,
                event_bus_name: str = None,
                model_id: str = None):
        """
        初期化
        
        Args:
            agent_id: エージェントID（指定しない場合は自動生成）
            agent_type: エージェントタイプ
            agent_state_table: エージェント状態テーブル名
            message_history_table: メッセージ履歴テーブル名
            artifacts_bucket: 成果物バケット名
            communication_queue_url: 通信キューURL
            event_bus_name: イベントバス名
            model_id: 使用するモデルID
        """
        self.agent_id = agent_id or f"{agent_type}-{str(uuid.uuid4())[:8]}"
        self.agent_type = agent_type
        self.created_at = datetime.utcnow().isoformat()
        self.state = "initialized"
        self.memory = []
        
        # クライアントの初期化
        if agent_state_table:
            self.state_db = DynamoDBClient(agent_state_table)
        
        if message_history_table:
            self.history_db = DynamoDBClient(message_history_table)
        
        if artifacts_bucket:
            self.artifacts = S3Client(artifacts_bucket)
        
        if communication_queue_url:
            self.queue = SQSClient(communication_queue_url)
        
        if event_bus_name:
            self.events = EventBridgeClient(event_bus_name)
        
        self.llm = LLMClient(model_id)
    
    def save_state(self) -> Dict[str, Any]:
        """
        エージェントの状態を保存
        
        Returns:
            保存結果
        """
        if not hasattr(self, 'state_db'):
            logger.warning("State DB not initialized, skipping save_state")
            return {}
        
        state_id = datetime.utcnow().isoformat()
        item = {
            'agentId': self.agent_id,
            'stateId': state_id,
            'agentType': self.agent_type,
            'state': self.state,
            'memory': json.dumps(self.memory),
            'createdAt': self.created_at,
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        return self.state_db.put_item(item)
    
    def load_state(self, state_id: str = None) -> bool:
        """
        エージェントの状態を読み込み
        
        Args:
            state_id: 読み込む状態ID（指定しない場合は最新）
            
        Returns:
            読み込み成功したかどうか
        """
        if not hasattr(self, 'state_db'):
            logger.warning("State DB not initialized, skipping load_state")
            return False
        
        try:
            if state_id:
                item = self.state_db.get_item({'agentId': self.agent_id, 'stateId': state_id})
            else:
                # 最新の状態を取得するためのクエリ（実装は簡略化）
                items = self.state_db.query(f"agentId = :agentId", 
                                          ExpressionAttributeValues={':agentId': self.agent_id},
                                          ScanIndexForward=False,
                                          Limit=1)
                item = items[0] if items else None
            
            if item:
                self.agent_type = item.get('agentType', self.agent_type)
                self.state = item.get('state', self.state)
                self.memory = json.loads(item.get('memory', '[]'))
                self.created_at = item.get('createdAt', self.created_at)
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            return False
    
    def add_to_memory(self, item: Any) -> None:
        """
        メモリにアイテムを追加
        
        Args:
            item: 追加するアイテム
        """
        self.memory.append(item)
    
    def send_message(self, recipient_id: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        他のエージェントにメッセージを送信
        
        Args:
            recipient_id: 受信者ID
            content: メッセージ内容
            
        Returns:
            送信結果
        """
        if not hasattr(self, 'queue'):
            logger.warning("Queue not initialized, skipping send_message")
            return {}
        
        message = {
            'sender_id': self.agent_id,
            'recipient_id': recipient_id,
            'content': content,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return self.queue.send_message(message)
    
    def receive_messages(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        メッセージを受信
        
        Args:
            max_messages: 最大メッセージ数
            
        Returns:
            受信したメッセージのリスト
        """
        if not hasattr(self, 'queue'):
            logger.warning("Queue not initialized, skipping receive_messages")
            return []
        
        return self.queue.receive_messages(max_messages)
    
    def emit_event(self, detail_type: str, detail: Dict[str, Any]) -> Dict[str, Any]:
        """
        イベントを発行
        
        Args:
            detail_type: イベント詳細タイプ
            detail: イベント詳細
            
        Returns:
            イベント発行結果
        """
        if not hasattr(self, 'events'):
            logger.warning("Event bus not initialized, skipping emit_event")
            return {}
        
        detail['agent_id'] = self.agent_id
        detail['agent_type'] = self.agent_type
        
        return self.events.put_event(
            source=f"agent.{self.agent_type}",
            detail_type=detail_type,
            detail=detail
        )
    
    def save_artifact(self, content: Union[str, Dict[str, Any]], key: str) -> Dict[str, Any]:
        """
        成果物を保存
        
        Args:
            content: 保存する内容
            key: 保存先キー
            
        Returns:
            保存結果
        """
        if not hasattr(self, 'artifacts'):
            logger.warning("Artifacts bucket not initialized, skipping save_artifact")
            return {}
        
        if isinstance(content, dict):
            return self.artifacts.upload_json(content, key)
        else:
            # 文字列の場合はJSONとして保存
            return self.artifacts.upload_json({'content': content}, key)
    
    def ask_llm(self, 
               messages: List[Dict[str, str]], 
               temperature: float = 0.7, 
               max_tokens: int = 4096) -> Dict[str, Any]:
        """
        LLMに質問
        
        Args:
            messages: メッセージのリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
            
        Returns:
            LLMからのレスポンス
        """
        return self.llm.invoke_llm(messages, temperature, max_tokens)
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        入力データを処理（サブクラスでオーバーライド）
        
        Args:
            input_data: 入力データ
            
        Returns:
            処理結果
        """
        raise NotImplementedError("Subclasses must implement process method")