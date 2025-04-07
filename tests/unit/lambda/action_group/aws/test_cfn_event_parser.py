import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import importlib.util

# Import the handler function from the module - using relative import to avoid 'lambda' keyword
import sys
import os

# Use a different import approach to avoid the 'lambda' keyword issue
cfn_event_parser_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'lambda', 'action_group', 'aws', 'cfn-event-parser')
sys.path.append(cfn_event_parser_path)

# モジュールのインポート前にsys.modulesをクリア
if 'index' in sys.modules:
    del sys.modules['index']

# 明示的にモジュールをロード
index_path = os.path.join(cfn_event_parser_path, 'index.py')
spec = importlib.util.spec_from_file_location("cfn_event_parser_index", index_path)
cfn_event_parser_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cfn_event_parser_index)

# ハンドラー関数を明示的に参照
handler = cfn_event_parser_index.handler

# Test constants
TEST_STACK_ID = "arn:aws:cloudformation:us-west-2:123456789012:stack/test-stack/abcdef"
TEST_STACK_NAME = "test-stack"
TEST_LOGICAL_RESOURCE_ID = "MyBucket"
TEST_RESOURCE_TYPE = "AWS::S3::Bucket"
TEST_STATUS = "CREATE_FAILED"
TEST_STATUS_REASON = "Resource creation failed: The specified bucket already exists"

@pytest.fixture
def mock_event():
    """基本的なCloudFormationイベントを作成"""
    return {
        "detail": {
            "stack-id": TEST_STACK_ID,
            "stack-name": TEST_STACK_NAME,
            "logical-resource-id": TEST_LOGICAL_RESOURCE_ID,
            "resource-type": TEST_RESOURCE_TYPE,
            "status": TEST_STATUS,
            "status-reason": TEST_STATUS_REASON
        }
    }

@pytest.fixture
def mock_boto3_client():
    """boto3クライアントのモックを作成"""
    mock_client = MagicMock()
    
    # describe_stacksのレスポンスを設定
    mock_client.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackName": TEST_STACK_NAME,
                "StackId": TEST_STACK_ID,
                "StackStatus": TEST_STATUS
            }
        ]
    }
    
    # get_templateのレスポンスを設定
    mock_client.get_template.return_value = {
        "TemplateBody": {
            "Resources": {
                TEST_LOGICAL_RESOURCE_ID: {
                    "Type": TEST_RESOURCE_TYPE,
                    "Properties": {
                        "BucketName": "existing-bucket-name"
                    }
                }
            }
        }
    }
    
    # describe_stack_eventsのレスポンスを設定
    mock_client.describe_stack_events.return_value = {
        "StackEvents": [
            {
                "LogicalResourceId": TEST_LOGICAL_RESOURCE_ID,
                "ResourceType": TEST_RESOURCE_TYPE,
                "ResourceStatus": "CREATE_FAILED",
                "ResourceStatusReason": TEST_STATUS_REASON,
                "Timestamp": datetime.now().isoformat()
            }
        ]
    }
    
    return mock_client

class TestCfnEventParser:
    """CloudFormationイベントパーサーのテストケース"""
    
    def test_handler_with_complete_event(self, mock_event, mock_boto3_client):
        """完全なイベント情報を持つ場合のハンドラーをテスト"""
        with patch('boto3.client', return_value=mock_boto3_client):
            result = handler(mock_event, {})
            
            # 結果を検証
            assert result["stackId"] == TEST_STACK_ID
            assert result["stackName"] == TEST_STACK_NAME
            assert result["logicalResourceId"] == TEST_LOGICAL_RESOURCE_ID
            assert result["resourceType"] == TEST_RESOURCE_TYPE
            assert result["status"] == TEST_STATUS
            assert result["statusReason"] == TEST_STATUS_REASON
            assert "timestamp" in result
            
            # boto3クライアントが呼び出されたことを検証
            mock_boto3_client.describe_stacks.assert_called_once_with(StackName=TEST_STACK_ID)
            mock_boto3_client.get_template.assert_called_once_with(StackName=TEST_STACK_ID, TemplateStage='Processed')
    
    def test_handler_with_incomplete_event(self, mock_boto3_client):
        """不完全なイベント情報を持つ場合のハンドラーをテスト"""
        # スタックIDのみを含むイベント
        incomplete_event = {
            "detail": {
                "stack-id": TEST_STACK_ID
            }
        }
        
        with patch('boto3.client', return_value=mock_boto3_client):
            result = handler(incomplete_event, {})
            
            # 結果を検証
            assert result["stackId"] == TEST_STACK_ID
            assert result["stackName"] == TEST_STACK_NAME
            assert "timestamp" in result
            
            # boto3クライアントが呼び出されたことを検証
            mock_boto3_client.describe_stacks.assert_called_once_with(StackName=TEST_STACK_ID)
            mock_boto3_client.get_template.assert_called_once()
            mock_boto3_client.describe_stack_events.assert_called_once()
    
    def test_handler_with_large_template(self, mock_event, mock_boto3_client):
        """大きなテンプレートを持つ場合のハンドラーをテスト"""
        # 大きなテンプレートを作成
        large_template = {
            "Resources": {
                TEST_LOGICAL_RESOURCE_ID: {
                    "Type": TEST_RESOURCE_TYPE,
                    "Properties": {
                        "BucketName": "existing-bucket-name"
                    }
                }
            }
        }
        # 50,000文字以上の文字列にする
        large_template_str = json.dumps(large_template) + "x" * 50000
        
        # get_templateのレスポンスを更新
        mock_boto3_client.get_template.return_value = {
            "TemplateBody": large_template_str
        }
        
        with patch('boto3.client', return_value=mock_boto3_client):
            result = handler(mock_event, {})
            
            # 結果を検証
            assert result["stackId"] == TEST_STACK_ID
            assert "templateSummary" in result
            assert result["hasTemplate"] is True
            assert "template" not in result
    
    def test_handler_with_boto3_error(self, mock_event):
        """boto3エラーが発生した場合のハンドラーをテスト"""
        # boto3.clientが例外を発生させるようにモック
        mock_error_client = MagicMock()
        mock_error_client.describe_stacks.side_effect = Exception("API Error")
        
        with patch('boto3.client', return_value=mock_error_client):
            with patch.object(cfn_event_parser_index, 'logging'):  # ログ出力を抑制
                result = handler(mock_event, {})
                
                # 結果を検証
                assert result["stackId"] == TEST_STACK_ID
                assert result["stackName"] == TEST_STACK_NAME
                assert "error" in result
                assert "API Error" in result["error"]
    
    def test_handler_with_template_parsing_error(self, mock_event, mock_boto3_client):
        """テンプレート解析エラーが発生した場合のハンドラーをテスト"""
        # get_templateのレスポンスを無効なJSONに設定
        mock_boto3_client.get_template.return_value = {
            "TemplateBody": "{ invalid json }"
        }
        
        with patch('boto3.client', return_value=mock_boto3_client):
            with patch.object(cfn_event_parser_index, 'logging'):  # ログ出力を抑制
                result = handler(mock_event, {})
                
                # 結果を検証
                assert result["stackId"] == TEST_STACK_ID
                assert result["stackName"] == TEST_STACK_NAME
                assert "template" in result
                assert result["template"] == "{ invalid json }"
