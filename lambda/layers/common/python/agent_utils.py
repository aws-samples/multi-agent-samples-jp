"""
エージェントフレームワークの共通ユーティリティ関数
"""
import json
import boto3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DynamoDBClient:
    """DynamoDBとのやり取りを行うクライアントクラス"""
    
    def __init__(self, table_name: str):
        """
        初期化
        
        Args:
            table_name: DynamoDBテーブル名
        """
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        アイテムを保存
        
        Args:
            item: 保存するアイテム
            
        Returns:
            DynamoDBのレスポンス
        """
        response = self.table.put_item(Item=item)
        return response
    
    def get_item(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        アイテムを取得
        
        Args:
            key: 取得するアイテムのキー
            
        Returns:
            取得したアイテム、存在しない場合はNone
        """
        response = self.table.get_item(Key=key)
        return response.get('Item')
    
    def query(self, key_condition_expression, **kwargs) -> List[Dict[str, Any]]:
        """
        クエリを実行
        
        Args:
            key_condition_expression: キー条件式
            **kwargs: その他のパラメータ
            
        Returns:
            クエリ結果のアイテムリスト
        """
        response = self.table.query(
            KeyConditionExpression=key_condition_expression,
            **kwargs
        )
        return response.get('Items', [])

class S3Client:
    """S3とのやり取りを行うクライアントクラス"""
    
    def __init__(self, bucket_name: str):
        """
        初期化
        
        Args:
            bucket_name: S3バケット名
        """
        self.s3 = boto3.client('s3')
        self.bucket_name = bucket_name
    
    def _get_artifact_sequence_number(self, project_id: str, agent_type: str, artifact_type: str) -> int:
        """
        特定のプロジェクト、エージェント、成果物タイプの最新シーケンス番号を取得
        
        Args:
            project_id: プロジェクトID
            agent_type: エージェントタイプ
            artifact_type: 成果物タイプ
            
        Returns:
            次のシーケンス番号（1から開始）
        """
        try:
            # 現在の年月を取得
            dt = datetime.now()
            year = dt.strftime('%Y')
            month = dt.strftime('%m')
            
            # プレフィックスを構築
            prefix = f"projects/{year}/{month}/{project_id}/{agent_type}/{artifact_type}/"
            
            # 既存のオブジェクトを一覧
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=1000  # 必要に応じて調整
            )
            
            # シーケンス番号を抽出
            max_seq = 0
            for item in response.get('Contents', []):
                key = item['Key']
                # キーからシーケンス番号を抽出
                # 形式: projects/{year}/{month}/{project_id}/{agent_type}/{artifact_type}/seq_{seq_num}_{artifact_id}.json
                filename = key.split('/')[-1]
                if filename.startswith('seq_'):
                    try:
                        seq_str = filename.split('_')[1]
                        seq_num = int(seq_str)
                        max_seq = max(max_seq, seq_num)
                    except (IndexError, ValueError):
                        continue
            
            # 次のシーケンス番号を返す
            return max_seq + 1
        except Exception as e:
            logging.warning(f"Failed to get sequence number: {str(e)}. Starting from 1.")
            return 1
    
    def _format_path(self, project_id: str, agent_type: str, artifact_type: str, 
                    artifact_id: str, timestamp: str = None, sequence_number: int = 1) -> str:
        """
        スケーラブルなS3パス構造を生成
        
        Args:
            project_id: プロジェクトID
            agent_type: エージェントタイプ (product_manager, architect, engineer)
            artifact_type: 成果物タイプ (analysis, user_stories, architecture)
            artifact_id: 成果物ID (UUID)
            timestamp: タイムスタンプ (ISO形式)
            sequence_number: シーケンス番号
            
        Returns:
            S3オブジェクトキー
        """
        if not timestamp:
            timestamp = datetime.now().isoformat()
            
        # タイムスタンプから年月を抽出
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            year = dt.strftime('%Y')
            month = dt.strftime('%m')
        except (ValueError, TypeError):
            # タイムスタンプのパースに失敗した場合は現在時刻を使用
            dt = datetime.now()
            year = dt.strftime('%Y')
            month = dt.strftime('%m')
        
        # シーケンス番号が1未満の場合は1に設定
        if sequence_number < 1:
            sequence_number = 1
            
        # スケーラブルなパス構造: projects/{year}/{month}/{project_id}/{agent_type}/{artifact_type}/seq_{sequence_number}_{artifact_id}.json
        return f"projects/{year}/{month}/{project_id}/{agent_type}/{artifact_type}/seq_{sequence_number}_{artifact_id}.json"
    
    def upload_file(self, file_path: str, object_key: str) -> Dict[str, Any]:
        """
        ファイルをアップロード
        
        Args:
            file_path: アップロードするファイルのパス
            object_key: S3オブジェクトキー
            
        Returns:
            S3のレスポンス
        """
        response = self.s3.upload_file(file_path, self.bucket_name, object_key)
        return response
    
    def upload_json(self, data: Dict[str, Any], object_key: str) -> Dict[str, Any]:
        """
        JSONデータをアップロード
        
        Args:
            data: アップロードするJSONデータ
            object_key: S3オブジェクトキー
            
        Returns:
            S3のレスポンス
        """
        json_data = json.dumps(data)
        response = self.s3.put_object(
            Body=json_data,
            Bucket=self.bucket_name,
            Key=object_key,
            ContentType='application/json'
        )
        return response
    
    def upload_artifact(self, data: Dict[str, Any], project_id: str, agent_type: str, 
                       artifact_type: str, artifact_id: str, timestamp: str = None) -> Dict[str, Any]:
        """
        成果物をスケーラブルなパス構造でアップロード
        
        Args:
            data: アップロードするJSONデータ
            project_id: プロジェクトID
            agent_type: エージェントタイプ
            artifact_type: 成果物タイプ
            artifact_id: 成果物ID
            timestamp: タイムスタンプ
            
        Returns:
            S3のレスポンスとパス情報
        """
        # シーケンス番号を自動的に取得
        sequence_number = self._get_artifact_sequence_number(project_id, agent_type, artifact_type)
        
        object_key = self._format_path(project_id, agent_type, artifact_type, artifact_id, timestamp, sequence_number)
        
        # シーケンス番号をデータに追加
        data['sequence_number'] = sequence_number
        
        response = self.upload_json(data, object_key)
        return {
            "response": response,
            "s3_key": object_key,
            "bucket": self.bucket_name,
            "sequence_number": sequence_number
        }
    
    def download_json(self, object_key: str) -> Dict[str, Any]:
        """
        JSONデータをダウンロード
        
        Args:
            object_key: S3オブジェクトキー
            
        Returns:
            ダウンロードしたJSONデータ
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket_name, Key=object_key)
            json_data = response['Body'].read().decode('utf-8')
            return json.loads(json_data)
        except Exception as e:
            logger.warning(f"Failed to download JSON from {object_key}: {str(e)}")
            raise
    
    def download_artifact(self, project_id: str, agent_type: str, artifact_type: str, 
                         artifact_id: str, timestamp: str = None) -> Dict[str, Any]:
        """
        成果物をスケーラブルなパス構造からダウンロード
        
        Args:
            project_id: プロジェクトID
            agent_type: エージェントタイプ
            artifact_type: 成果物タイプ
            artifact_id: 成果物ID
            timestamp: タイムスタンプ
            
        Returns:
            ダウンロードしたJSONデータ
        """
        try:
            # 現在の年月を取得
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    dt = datetime.now()
            else:
                dt = datetime.now()
            
            year = dt.strftime('%Y')
            month = dt.strftime('%m')
            
            # プレフィックスを構築
            prefix = f"projects/{year}/{month}/{project_id}/{agent_type}/{artifact_type}/"
            
            # 既存のオブジェクトを一覧
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            # artifact_idに一致するオブジェクトを検索し、最新のシーケンス番号を持つものを取得
            matching_keys = []
            for item in response.get('Contents', []):
                key = item['Key']
                filename = key.split('/')[-1]
                if f"_{artifact_id}.json" in filename:
                    try:
                        seq_str = filename.split('_')[1]
                        seq_num = int(seq_str)
                        matching_keys.append((seq_num, key))
                    except (IndexError, ValueError):
                        continue
            
            if matching_keys:
                # シーケンス番号で降順ソートして最新のものを取得
                matching_keys.sort(reverse=True)
                _, object_key = matching_keys[0]
                return self.download_json(object_key)
            
            # 一致するものがない場合はシーケンス番号1でパスを生成
            logging.warning(f"No matching artifact found with sequence number. Using sequence_number=1.")
            sequence_number = 1
        except Exception as e:
            logging.warning(f"Error finding artifact with sequence: {str(e)}. Using sequence_number=1.")
            sequence_number = 1
        
        # シーケンス番号を使用してパスを生成
        object_key = self._format_path(project_id, agent_type, artifact_type, artifact_id, timestamp, sequence_number)
        return self.download_json(object_key)
    
    def list_artifacts(self, project_id: str = None, year: str = None, month: str = None, 
                      agent_type: str = None, artifact_type: str = None, max_items: int = 100) -> List[Dict[str, Any]]:
        """
        成果物の一覧を取得
        
        Args:
            project_id: プロジェクトID (オプション)
            year: 年 (オプション)
            month: 月 (オプション)
            agent_type: エージェントタイプ (オプション)
            artifact_type: 成果物タイプ (オプション)
            max_items: 最大アイテム数
            
        Returns:
            成果物の一覧
        """
        # プレフィックスを構築
        prefix = "projects/"
        if year:
            prefix += f"{year}/"
            if month:
                prefix += f"{month}/"
        
        if project_id:
            if not year or not month:
                # プロジェクトIDが指定されている場合は年月も必要
                current_year = datetime.now().strftime('%Y')
                current_month = datetime.now().strftime('%m')
                prefix += f"{current_year}/{current_month}/{project_id}/"
            else:
                prefix += f"{project_id}/"
                
            if agent_type:
                prefix += f"{agent_type}/"
                if artifact_type:
                    prefix += f"{artifact_type}/"
        
        # S3オブジェクトの一覧を取得
        response = self.s3.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=prefix,
            MaxKeys=max_items
        )
        
        # 結果を整形
        artifacts = []
        for item in response.get('Contents', []):
            artifacts.append({
                "key": item['Key'],
                "size": item['Size'],
                "last_modified": item['LastModified'].isoformat(),
                "etag": item['ETag']
            })
            
        return artifacts

class SQSClient:
    """SQSとのやり取りを行うクライアントクラス"""
    
    def __init__(self, queue_url: str):
        """
        初期化
        
        Args:
            queue_url: SQSキューのURL
        """
        self.sqs = boto3.client('sqs')
        self.queue_url = queue_url
    
    def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        メッセージを送信
        
        Args:
            message: 送信するメッセージ
            
        Returns:
            SQSのレスポンス
        """
        response = self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message)
        )
        return response
    
    def receive_messages(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        メッセージを受信
        
        Args:
            max_messages: 最大メッセージ数
            
        Returns:
            受信したメッセージのリスト
        """
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=20
        )
        return response.get('Messages', [])
    
    def delete_message(self, receipt_handle: str) -> Dict[str, Any]:
        """
        メッセージを削除
        
        Args:
            receipt_handle: 削除するメッセージのレシートハンドル
            
        Returns:
            SQSのレスポンス
        """
        response = self.sqs.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )
        return response

class EventBridgeClient:
    """EventBridgeとのやり取りを行うクライアントクラス"""
    
    def __init__(self, event_bus_name: str):
        """
        初期化
        
        Args:
            event_bus_name: EventBusの名前
        """
        self.events = boto3.client('events')
        self.event_bus_name = event_bus_name
    
    def put_event(self, source: str, detail_type: str, detail: Dict[str, Any]) -> Dict[str, Any]:
        """
        イベントを送信
        
        Args:
            source: イベントソース
            detail_type: イベント詳細タイプ
            detail: イベント詳細
            
        Returns:
            EventBridgeのレスポンス
        """
        response = self.events.put_events(
            Entries=[
                {
                    'Source': source,
                    'DetailType': detail_type,
                    'Detail': json.dumps(detail),
                    'EventBusName': self.event_bus_name
                }
            ]
        )
        return response