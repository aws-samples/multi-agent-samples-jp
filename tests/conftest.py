"""
Pytest共通設定ファイル
"""
import os
import sys
import pytest
import logging
from unittest.mock import MagicMock, patch

# ログレベルを設定して不要なログ出力を抑制
logging.basicConfig(level=logging.ERROR)

# プロジェクトのルートディレクトリをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# テスト対象のコードをインポートできるようにパスを追加
sys.path.append(os.path.join(project_root, 'lambda'))
sys.path.append(os.path.join(project_root, 'lambda/layers/common/python'))

# 各エージェントのパスを明示的に設定
product_manager_path = os.path.join(project_root, 'lambda', 'action_group', 'bizdev', 'product-manager')
architect_path = os.path.join(project_root, 'lambda', 'action_group', 'bizdev', 'architect')
engineer_path = os.path.join(project_root, 'lambda', 'action_group', 'bizdev', 'engineer')
cloud_architect_path = os.path.join(project_root, 'lambda', 'action_group', 'aws', 'cloud-architect')
serverless_architect_path = os.path.join(project_root, 'lambda', 'action_group', 'aws', 'serverless-architect')
cfn_event_parser_path = os.path.join(project_root, 'lambda', 'action_group', 'aws', 'cfn-event-parser')

sys.path.append(product_manager_path)
sys.path.append(architect_path)
sys.path.append(engineer_path)
sys.path.append(cloud_architect_path)
sys.path.append(serverless_architect_path)
sys.path.append(cfn_event_parser_path)

# テスト実行前に各テストで使用するモジュールのキャッシュをクリア
@pytest.fixture(autouse=True)
def clear_module_cache():
    """テスト実行前にモジュールキャッシュをクリア"""
    if 'index' in sys.modules:
        del sys.modules['index']
    yield

# テスト実行中のログ出力を抑制
@pytest.fixture(autouse=True)
def suppress_logging():
    """テスト実行中のログ出力を抑制"""
    with patch('logging.Logger.info'), patch('logging.Logger.debug'), patch('logging.Logger.warning'):
        yield

# 共通のフィクスチャー
@pytest.fixture
def mock_dynamodb_client():
    """DynamoDBクライアントのモック"""
    mock = MagicMock()
    return mock

@pytest.fixture
def mock_s3_client():
    """S3クライアントのモック"""
    mock = MagicMock()
    return mock

@pytest.fixture
def mock_sqs_client():
    """SQSクライアントのモック"""
    mock = MagicMock()
    return mock

@pytest.fixture
def mock_eventbridge_client():
    """EventBridgeクライアントのモック"""
    mock = MagicMock()
    return mock
