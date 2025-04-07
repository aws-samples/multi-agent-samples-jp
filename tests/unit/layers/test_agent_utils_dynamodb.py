"""
DynamoDBClientのテスト
"""
import pytest
from unittest.mock import MagicMock, patch
from agent_utils import DynamoDBClient


@patch('agent_utils.boto3.resource')
def test_dynamodb_client_init(mock_boto3_resource):
    """DynamoDBClientの初期化テスト"""
    # モックの設定
    mock_table = MagicMock()
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_boto3_resource.return_value = mock_resource
    
    # テスト対象のクラスをインスタンス化
    table_name = "test_table"
    client = DynamoDBClient(table_name)
    
    # 検証
    assert client.table == mock_table
    mock_boto3_resource.assert_called_once_with('dynamodb')
    mock_resource.Table.assert_called_once_with(table_name)


@patch('agent_utils.boto3.resource')
def test_put_item(mock_boto3_resource):
    """put_itemメソッドのテスト"""
    # モックの設定
    mock_table = MagicMock()
    mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_boto3_resource.return_value = mock_resource
    
    # テスト対象のクラスをインスタンス化
    client = DynamoDBClient("test_table")
    
    # テスト実行
    item = {"id": "1", "name": "test"}
    response = client.put_item(item)
    
    # 検証
    mock_table.put_item.assert_called_once_with(Item=item)
    assert response == {"ResponseMetadata": {"HTTPStatusCode": 200}}


@patch('agent_utils.boto3.resource')
def test_get_item_exists(mock_boto3_resource):
    """get_itemメソッドのテスト（アイテムが存在する場合）"""
    # モックの設定
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {"id": "1", "name": "test"},
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_boto3_resource.return_value = mock_resource
    
    # テスト対象のクラスをインスタンス化
    client = DynamoDBClient("test_table")
    
    # テスト実行
    key = {"id": "1"}
    item = client.get_item(key)
    
    # 検証
    mock_table.get_item.assert_called_once_with(Key=key)
    assert item == {"id": "1", "name": "test"}


@patch('agent_utils.boto3.resource')
def test_get_item_not_exists(mock_boto3_resource):
    """get_itemメソッドのテスト（アイテムが存在しない場合）"""
    # モックの設定
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_boto3_resource.return_value = mock_resource
    
    # テスト対象のクラスをインスタンス化
    client = DynamoDBClient("test_table")
    
    # テスト実行
    key = {"id": "1"}
    item = client.get_item(key)
    
    # 検証
    mock_table.get_item.assert_called_once_with(Key=key)
    assert item is None


@patch('agent_utils.boto3.resource')
def test_query(mock_boto3_resource):
    """queryメソッドのテスト"""
    # モックの設定
    mock_table = MagicMock()
    mock_table.query.return_value = {
        "Items": [
            {"id": "1", "name": "test1"},
            {"id": "2", "name": "test2"}
        ],
        "Count": 2,
        "ScannedCount": 2,
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_boto3_resource.return_value = mock_resource
    
    # テスト対象のクラスをインスタンス化
    client = DynamoDBClient("test_table")
    
    # テスト実行
    key_condition = "id = :id"
    expression_values = {":id": "1"}
    items = client.query(
        key_condition,
        ExpressionAttributeValues=expression_values,
        Limit=10
    )
    
    # 検証
    mock_table.query.assert_called_once_with(
        KeyConditionExpression=key_condition,
        ExpressionAttributeValues=expression_values,
        Limit=10
    )
    assert len(items) == 2
    assert items[0]["name"] == "test1"
    assert items[1]["name"] == "test2"


@patch('agent_utils.boto3.resource')
def test_query_empty_result(mock_boto3_resource):
    """queryメソッドのテスト（結果が空の場合）"""
    # モックの設定
    mock_table = MagicMock()
    mock_table.query.return_value = {
        "Items": [],
        "Count": 0,
        "ScannedCount": 0,
        "ResponseMetadata": {"HTTPStatusCode": 200}
    }
    
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    mock_boto3_resource.return_value = mock_resource
    
    # テスト対象のクラスをインスタンス化
    client = DynamoDBClient("test_table")
    
    # テスト実行
    key_condition = "id = :id"
    expression_values = {":id": "999"}
    items = client.query(
        key_condition,
        ExpressionAttributeValues=expression_values
    )
    
    # 検証
    mock_table.query.assert_called_once_with(
        KeyConditionExpression=key_condition,
        ExpressionAttributeValues=expression_values
    )
    assert len(items) == 0