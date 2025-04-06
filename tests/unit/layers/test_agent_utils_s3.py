"""
S3Clientのテスト
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from agent_utils import S3Client


@patch('agent_utils.boto3.client')
def test_s3_client_init(mock_boto3_client):
    """S3Clientの初期化テスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-bucket"
    client = S3Client(bucket_name)
    
    # 検証
    assert client.s3 == mock_client
    assert client.bucket_name == bucket_name
    mock_boto3_client.assert_called_once_with('s3')


@patch('agent_utils.boto3.client')
def test_upload_json(mock_boto3_client):
    """upload_jsonメソッドのテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-bucket"
    client = S3Client(bucket_name)
    
    # テスト実行
    data = {"id": "1", "name": "test"}
    object_key = "test/path/file.json"
    response = client.upload_json(data, object_key)
    
    # 検証
    mock_client.put_object.assert_called_once_with(
        Body=json.dumps(data),
        Bucket=bucket_name,
        Key=object_key,
        ContentType='application/json'
    )
    assert response == {"ResponseMetadata": {"HTTPStatusCode": 200}}


@patch('agent_utils.boto3.client')
def test_download_json(mock_boto3_client):
    """download_jsonメソッドのテスト"""
    # モックの設定
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({"id": "1", "name": "test"}).encode('utf-8')
    
    mock_client = MagicMock()
    mock_client.get_object.return_value = {
        "Body": mock_body,
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-bucket"
    client = S3Client(bucket_name)
    
    # テスト実行
    object_key = "test/path/file.json"
    data = client.download_json(object_key)
    
    # 検証
    mock_client.get_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=object_key
    )
    assert data == {"id": "1", "name": "test"}


@patch('agent_utils.boto3.client')
def test_download_json_error(mock_boto3_client):
    """download_jsonメソッドのエラーテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.get_object.side_effect = Exception("File not found")
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-bucket"
    client = S3Client(bucket_name)
    
    # テスト実行とエラー検証
    object_key = "test/path/not_exists.json"
    with pytest.raises(Exception) as e:
        client.download_json(object_key)
    
    assert str(e.value) == "File not found"
    mock_client.get_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=object_key
    )


@patch('agent_utils.boto3.client')
def test_format_path(mock_boto3_client):
    """_format_pathメソッドのテスト"""
    # モックの設定
    mock_boto3_client.return_value = MagicMock()
    
    # テスト対象のクラスをインスタンス化
    client = S3Client("test-bucket")
    
    # テスト実行 - タイムスタンプを指定
    timestamp = "2023-05-15T10:30:45.123456"
    path = client._format_path(
        project_id="proj123",
        agent_type="product_manager",
        artifact_type="analysis",
        artifact_id="abc123",
        timestamp=timestamp,
        sequence_number=5
    )
    
    # 検証
    expected_path = "projects/2023/05/proj123/product_manager/analysis/seq_5_abc123.json"
    assert path == expected_path
    
    # テスト実行 - タイムスタンプを指定しない場合
    with patch('agent_utils.datetime') as mock_datetime:
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: "2023" if fmt == '%Y' else "06"
        mock_datetime.now.return_value = mock_now
        
        # fromisoformatのモックを適切に設定
        mock_dt = MagicMock()
        mock_dt.strftime.side_effect = lambda fmt: "2023" if fmt == '%Y' else "06"
        mock_datetime.fromisoformat.return_value = mock_dt
        
        path = client._format_path(
            project_id="proj123",
            agent_type="product_manager",
            artifact_type="analysis",
            artifact_id="abc123",
            sequence_number=1
        )
    
    # 検証
    expected_path = "projects/2023/06/proj123/product_manager/analysis/seq_1_abc123.json"
    assert path == expected_path


@patch('agent_utils.boto3.client')
def test_get_artifact_sequence_number(mock_boto3_client):
    """_get_artifact_sequence_numberメソッドのテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "projects/2023/05/proj123/product_manager/analysis/seq_1_abc123.json"},
            {"Key": "projects/2023/05/proj123/product_manager/analysis/seq_3_def456.json"},
            {"Key": "projects/2023/05/proj123/product_manager/analysis/seq_2_ghi789.json"}
        ]
    }
    mock_boto3_client.return_value = mock_client
    
    # 現在の年月をモック
    with patch('agent_utils.datetime') as mock_datetime:
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: "2023" if fmt == '%Y' else "05"
        mock_datetime.now.return_value = mock_now
        
        # テスト対象のクラスをインスタンス化
        client = S3Client("test-bucket")
        
        # テスト実行
        seq_num = client._get_artifact_sequence_number(
            project_id="proj123",
            agent_type="product_manager",
            artifact_type="analysis"
        )
    
    # 検証
    expected_prefix = "projects/2023/05/proj123/product_manager/analysis/"
    mock_client.list_objects_v2.assert_called_once_with(
        Bucket="test-bucket",
        Prefix=expected_prefix,
        MaxKeys=1000
    )
    # 最大のシーケンス番号 + 1 が返されるはず
    assert seq_num == 4


@patch('agent_utils.boto3.client')
def test_get_artifact_sequence_number_no_objects(mock_boto3_client):
    """_get_artifact_sequence_numberメソッドのテスト（オブジェクトがない場合）"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {}  # Contentsキーなし
    mock_boto3_client.return_value = mock_client
    
    # 現在の年月をモック
    with patch('agent_utils.datetime') as mock_datetime:
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: "2023" if fmt == '%Y' else "05"
        mock_datetime.now.return_value = mock_now
        
        # テスト対象のクラスをインスタンス化
        client = S3Client("test-bucket")
        
        # テスト実行
        seq_num = client._get_artifact_sequence_number(
            project_id="proj123",
            agent_type="product_manager",
            artifact_type="analysis"
        )
    
    # オブジェクトがない場合は1が返されるはず
    assert seq_num == 1


@patch('agent_utils.boto3.client')
def test_upload_artifact(mock_boto3_client):
    """upload_artifactメソッドのテスト"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-bucket"
    client = S3Client(bucket_name)
    
    # _get_artifact_sequence_numberをモック
    with patch.object(client, '_get_artifact_sequence_number', return_value=5):
        # _format_pathをモック
        with patch.object(client, '_format_path', return_value="projects/2023/05/proj123/product_manager/analysis/seq_5_abc123.json"):
            # テスト実行
            data = {"id": "1", "name": "test"}
            result = client.upload_artifact(
                data=data,
                project_id="proj123",
                agent_type="product_manager",
                artifact_type="analysis",
                artifact_id="abc123",
                timestamp="2023-05-15T10:30:45"
            )
    
    # 検証
    # sequence_numberがデータに追加されているか
    expected_data = {"id": "1", "name": "test", "sequence_number": 5}
    mock_client.put_object.assert_called_once_with(
        Body=json.dumps(expected_data),
        Bucket=bucket_name,
        Key="projects/2023/05/proj123/product_manager/analysis/seq_5_abc123.json",
        ContentType='application/json'
    )
    
    # 返り値の検証
    assert result["s3_key"] == "projects/2023/05/proj123/product_manager/analysis/seq_5_abc123.json"
    assert result["bucket"] == bucket_name
    assert result["sequence_number"] == 5


@patch('agent_utils.boto3.client')
def test_download_artifact(mock_boto3_client):
    """download_artifactメソッドのテスト（正常系）"""
    # モックの設定
    mock_client = MagicMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "projects/2023/05/proj123/product_manager/analysis/seq_1_abc123.json"},
            {"Key": "projects/2023/05/proj123/product_manager/analysis/seq_3_abc123.json"},
            {"Key": "projects/2023/05/proj123/product_manager/analysis/seq_2_abc123.json"}
        ]
    }
    mock_boto3_client.return_value = mock_client
    
    # テスト対象のクラスをインスタンス化
    bucket_name = "test-bucket"
    client = S3Client(bucket_name)
    
    # download_jsonの戻り値をモック
    expected_data = {"id": "abc123", "name": "test", "sequence_number": 3}
    # MagicMockを使用して明示的にモック
    mock_download_json = MagicMock(return_value=expected_data)
    
    with patch.object(client, 'download_json', mock_download_json):
        # 現在の年月をモック
        with patch('agent_utils.datetime') as mock_datetime:
            mock_datetime.fromisoformat.return_value = datetime(2023, 5, 15)
            
            # テスト実行
            data = client.download_artifact(
                project_id="proj123",
                agent_type="product_manager",
                artifact_type="analysis",
                artifact_id="abc123",
                timestamp="2023-05-15T10:30:45"
            )
    
    # 検証
    expected_prefix = "projects/2023/05/proj123/product_manager/analysis/"
    mock_client.list_objects_v2.assert_called_once_with(
        Bucket=bucket_name,
        Prefix=expected_prefix
    )
    
    # 最新のシーケンス番号のオブジェクトが選択されているはず
    mock_download_json.assert_called_once_with("projects/2023/05/proj123/product_manager/analysis/seq_3_abc123.json")
    assert data == expected_data