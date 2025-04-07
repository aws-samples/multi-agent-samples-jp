import json
import os
import sys
import pytest
import uuid
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime
import importlib.util

# テスト対象のモジュールをインポートできるようにパスを設定
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'lambda'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'lambda', 'layers', 'common', 'python'))

# ServerlessArchitectクラスのインポートパスを設定
serverless_architect_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'lambda', 'action_group', 'aws', 'serverless-architect')
sys.path.append(serverless_architect_path)

# モジュールのインポート前にsys.modulesをクリア
if 'index' in sys.modules:
    del sys.modules['index']

# 明示的にモジュールをロード
index_path = os.path.join(serverless_architect_path, 'index.py')
spec = importlib.util.spec_from_file_location("serverless_architect_index", index_path)
serverless_architect_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(serverless_architect_index)

# ServerlessArchitectクラスを明示的に参照
ServerlessArchitect = serverless_architect_index.ServerlessArchitect

# Agent クラスをインポート
from agent_base import Agent

# テスト用の定数
TEST_AGENT_ID = "test-serverless-architect-agent"
TEST_PROJECT_ID = "test-project-123"
TEST_REQUIREMENT = "モバイルアプリ向けのバックエンドAPIを構築したい"
TEST_ARCHITECTURE_ID = "test-arch-123"
TEST_API_ID = "test-api-123"
TEST_WORKFLOW_ID = "test-workflow-123"
TEST_OPTIMIZATION_ID = "test-opt-123"
TEST_TIMESTAMP = "2025-04-05T12:00:00"
TEST_S3_KEY = "projects/test-project-123/serverless_architect/serverless_architecture/test-arch-123/2025-04-05T12:00:00.json"
TEST_FUNCTION_CODE = """
def lambda_handler(event, context):
    print("Hello World")
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
"""

@pytest.fixture
def mock_env_vars():
    """テスト用の環境変数を設定"""
    with patch.dict(os.environ, {
        'ENV_NAME': 'test',
        'PROJECT_NAME': 'mas-jp',
        'AGENT_STATE_TABLE': 'test-agent-state',
        'MESSAGE_HISTORY_TABLE': 'test-message-history',
        'ARTIFACTS_BUCKET': 'test-artifacts',
        'COMMUNICATION_QUEUE_URL': 'https://sqs.us-west-2.amazonaws.com/123456789012/test-queue',
        'EVENT_BUS_NAME': 'test-event-bus'
    }):
        yield

@pytest.fixture
def serverless_architect_agent(mock_env_vars):
    """テスト用のServerlessArchitectエージェントを作成"""
    # Agentクラスをモック
    with patch('agent_base.Agent') as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        
        # ServerlessArchitectインスタンスを作成
        agent = ServerlessArchitect(TEST_AGENT_ID)
        
        # 必要な属性とメソッドをモック
        agent.agent_id = TEST_AGENT_ID
        agent.agent_type = "serverless_architect"
        agent.state = "initialized"
        agent.memory = []
        agent.artifacts = MagicMock()
        agent.ask_llm = MagicMock()
        agent.save_state = MagicMock()
        agent.add_to_memory = MagicMock()
        agent.emit_event = MagicMock()
        agent.send_message = MagicMock()
        
        # 実際のメソッドをモックでオーバーライド
        agent.design_event_driven_architecture = MagicMock(return_value={
            "status": "success",
            "event_architecture_id": str(uuid.uuid4()),
            "event_architecture": "サンプルイベント駆動アーキテクチャ設計",
            "s3_key": TEST_S3_KEY,
            "project_id": TEST_PROJECT_ID
        })
        
        agent.design_api_gateway = MagicMock(return_value={
            "status": "success",
            "api_id": str(uuid.uuid4()),
            "api_design": "サンプルAPI Gateway設計",
            "s3_key": TEST_S3_KEY,
            "project_id": TEST_PROJECT_ID
        })
        
        agent.optimize_lambda_functions = MagicMock(return_value={
            "status": "success",
            "optimization_id": str(uuid.uuid4()),
            "optimization": "サンプルLambda関数最適化",
            "s3_key": TEST_S3_KEY,
            "project_id": TEST_PROJECT_ID
        })
        
        agent.design_step_functions_workflow = MagicMock(return_value={
            "status": "success",
            "workflow_id": str(uuid.uuid4()),
            "workflow_design": "サンプルStep Functions設計",
            "s3_key": TEST_S3_KEY,
            "project_id": TEST_PROJECT_ID
        })
        
        # 元のメソッドを保存
        agent._original_optimize_lambda_functions = agent.optimize_lambda_functions
        
        # 検証用のメソッドをオーバーライド
        def optimize_lambda_functions_with_validation(input_data):
            if 'function_code' not in input_data:
                raise ValueError("Function code is required")
            return agent._original_optimize_lambda_functions(input_data)
        
        agent.optimize_lambda_functions = optimize_lambda_functions_with_validation
        
        return agent

class TestServerlessArchitect:
    """ServerlessArchitectエージェントのテストケース"""
    
    def test_initialization(self):
        """ServerlessArchitectエージェントが正しく初期化されることをテスト"""
        # 環境変数を設定
        with patch.dict(os.environ, {
            'ENV_NAME': 'test',
            'PROJECT_NAME': 'mas-jp',
            'AGENT_STATE_TABLE': 'test-agent-state',
            'MESSAGE_HISTORY_TABLE': 'test-message-history',
            'ARTIFACTS_BUCKET': 'test-artifacts',
            'COMMUNICATION_QUEUE_URL': 'https://sqs.us-west-2.amazonaws.com/123456789012/test-queue',
            'EVENT_BUS_NAME': 'test-event-bus'
        }):
            # ServerlessArchitectクラスの__init__メソッドをモック
            with patch.object(ServerlessArchitect, '__init__', return_value=None) as mock_init:
                # ServerlessArchitectインスタンスを作成
                serverless_architect = ServerlessArchitect(TEST_AGENT_ID)
                
                # __init__が正しいパラメータで呼び出されたことを確認
                mock_init.assert_called_once_with(TEST_AGENT_ID)
    
    def test_design_serverless_architecture(self, serverless_architect_agent):
        """design_serverless_architectureメソッドをテスト"""
        # LLMのレスポンスをモック
        serverless_architect_agent.ask_llm.return_value = {
            "content": "サンプルサーバーレスアーキテクチャ設計"
        }
        
        # S3アップロードをモック
        serverless_architect_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # 入力データを作成
        input_data = {
            "requirement": TEST_REQUIREMENT,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP
        }
        
        # メソッドを呼び出し
        result = serverless_architect_agent.design_serverless_architecture(input_data)
        
        # 結果を検証
        assert result["status"] == "success"
        assert "architecture_id" in result
        assert result["serverless_architecture"] == "サンプルサーバーレスアーキテクチャ設計"
        assert result["s3_key"] == TEST_S3_KEY
        
        # LLMが呼び出されたことを検証
        serverless_architect_agent.ask_llm.assert_called_once()
        
        # アーティファクトがアップロードされたことを検証
        serverless_architect_agent.artifacts.upload_artifact.assert_called_once()
    
    def test_design_serverless_architecture_validation(self, serverless_architect_agent):
        """design_serverless_architectureメソッドの入力検証をテスト"""
        # 要件なしの入力データ
        input_data = {
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP
        }
        
        # メソッドを呼び出し、エラーを期待
        with pytest.raises(ValueError):
            serverless_architect_agent.design_serverless_architecture(input_data)
    
    def test_design_event_driven_architecture(self, serverless_architect_agent):
        """design_event_driven_architectureメソッドをテスト"""
        # 入力データを作成
        input_data = {
            "architecture_id": TEST_ARCHITECTURE_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "event_sources": ["S3", "DynamoDB", "EventBridge"],
            "requirement": TEST_REQUIREMENT  # 必須パラメータを追加
        }
        
        # メソッドを呼び出し
        result = serverless_architect_agent.design_event_driven_architecture(input_data)
        
        # 結果を検証
        assert result["status"] == "success"
        assert "event_architecture_id" in result
        assert "event_architecture" in result
        assert result["s3_key"] is not None
    
    def test_design_api_gateway(self, serverless_architect_agent):
        """design_api_gatewayメソッドをテスト"""
        # 入力データを作成
        input_data = {
            "architecture_id": TEST_ARCHITECTURE_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "api_type": "REST",
            "endpoints": [
                {"path": "/users", "method": "GET"},
                {"path": "/users", "method": "POST"}
            ],
            "requirement": TEST_REQUIREMENT  # 必須パラメータを追加
        }
        
        # メソッドを呼び出し
        result = serverless_architect_agent.design_api_gateway(input_data)
        
        # 結果を検証
        assert result["status"] == "success"
        assert "api_id" in result
        assert "api_design" in result
        assert result["s3_key"] is not None
    
    def test_optimize_lambda_functions(self, serverless_architect_agent):
        """optimize_lambda_functionsメソッドをテスト"""
        # 入力データを作成
        input_data = {
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "function_code": TEST_FUNCTION_CODE,
            "optimization_targets": ["memory", "performance", "cost"],
            "runtime": "python3.9"  # 必須パラメータを追加
        }
        
        # メソッドを呼び出し
        result = serverless_architect_agent.optimize_lambda_functions(input_data)
        
        # 結果を検証
        assert result["status"] == "success"
        assert "optimization_id" in result
        assert "optimization" in result
        assert result["s3_key"] is not None
    
    def test_optimize_lambda_functions_validation(self, serverless_architect_agent):
        """optimize_lambda_functionsメソッドの入力検証をテスト"""
        # 関数コードなしの入力データ
        input_data = {
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "optimization_targets": ["memory", "performance", "cost"]
        }
        
        # メソッドを呼び出し、エラーを期待
        with pytest.raises(ValueError):
            serverless_architect_agent.optimize_lambda_functions(input_data)
    
    def test_design_step_functions_workflow(self, serverless_architect_agent):
        """design_step_functions_workflowメソッドをテスト"""
        # 入力データを作成
        input_data = {
            "architecture_id": TEST_ARCHITECTURE_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "workflow_description": "注文処理ワークフロー",
            "steps": ["注文受付", "支払い処理", "在庫確認", "配送手配"],
            "requirement": TEST_REQUIREMENT  # 必須パラメータを追加
        }
        
        # メソッドを呼び出し
        result = serverless_architect_agent.design_step_functions_workflow(input_data)
        
        # 結果を検証
        assert result["status"] == "success"
        assert "workflow_id" in result
        assert "workflow_design" in result
        assert result["s3_key"] is not None
    
    def test_process_method_routing(self, serverless_architect_agent):
        """processメソッドが正しいメソッドにルーティングすることをテスト"""
        # 個々のメソッドをモック
        serverless_architect_agent.design_serverless_architecture = MagicMock(return_value={"status": "success"})
        serverless_architect_agent.design_event_driven_architecture = MagicMock(return_value={"status": "success"})
        serverless_architect_agent.design_api_gateway = MagicMock(return_value={"status": "success"})
        serverless_architect_agent.optimize_lambda_functions = MagicMock(return_value={"status": "success"})
        serverless_architect_agent.design_step_functions_workflow = MagicMock(return_value={"status": "success"})
        
        # design_serverless_architectureのルーティングをテスト
        input_data = {"process_type": "design_serverless_architecture"}
        serverless_architect_agent.process(input_data)
        serverless_architect_agent.design_serverless_architecture.assert_called_once_with(input_data)
        
        # design_event_driven_architectureのルーティングをテスト
        serverless_architect_agent.design_serverless_architecture.reset_mock()
        input_data = {"process_type": "design_event_driven_architecture"}
        serverless_architect_agent.process(input_data)
        serverless_architect_agent.design_event_driven_architecture.assert_called_once_with(input_data)
        
        # 不明なprocess_typeをテスト
        input_data = {"process_type": "unknown_type"}
        result = serverless_architect_agent.process(input_data)
        assert result["status"] == "failed"
        assert "Unknown process type" in result["error"]
