import json
import os
import sys
import pytest
import uuid
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

# Import the Engineer class from the module using a different approach
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../lambda'))
from action_group.bizdev.engineer.index import Engineer

# Test constants
TEST_AGENT_ID = "test-engineer-agent"
TEST_PROJECT_ID = "test-project-123"
TEST_REQUIREMENT = "Create a mobile app for household finance management"
TEST_IMPLEMENTATION_ID = "test-impl-123"
TEST_REVIEW_ID = "test-review-123"
TEST_FIXED_ID = "test-fixed-123"
TEST_TIMESTAMP = "2025-04-05T12:00:00"
TEST_USER_ID = "test-user-123"
TEST_PRD_ID = "test-prd-123"
TEST_ARCHITECTURE_ID = "test-arch-123"
TEST_S3_KEY = "projects/test-project-123/engineer/implementation/test-impl-123/2025-04-05T12:00:00.json"

@pytest.fixture
def mock_env_vars():
    """Set up environment variables for testing"""
    with patch.dict(os.environ, {
        'ENV_NAME': 'test',
        'PROJECT_NAME': 'mas-jp',
        'AGENT_STATE_TABLE': 'test-agent-state',
        'MESSAGE_HISTORY_TABLE': 'test-message-history',
        'ARTIFACTS_BUCKET': 'test-artifacts',
        'COMMUNICATION_QUEUE_URL': 'https://sqs.us-west-2.amazonaws.com/123456789012/test-queue',
        'EVENT_BUS_NAME': 'test-event-bus',
        'CODE_EXECUTION_PROJECT': 'test-codebuild-project'
    }):
        yield

@pytest.fixture
def engineer_agent(mock_env_vars):
    """Create an Engineer agent for testing"""
    # Import Agent class using the same approach to avoid 'lambda' keyword
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../lambda/layers/common/python'))
    with patch('action_group.bizdev.engineer.index.Agent.__init__') as mock_init:
        mock_init.return_value = None
        agent = Engineer(TEST_AGENT_ID)
        
        # Mock the necessary attributes and methods
        agent.agent_id = TEST_AGENT_ID
        agent.agent_type = "engineer"
        agent.state = "initialized"
        agent.memory = []
        agent.artifacts = MagicMock()
        agent.ask_llm = MagicMock()
        agent.save_state = MagicMock()
        agent.add_to_memory = MagicMock()
        agent.emit_event = MagicMock()
        agent.send_message = MagicMock()
        
        return agent

class TestEngineer:
    """Test cases for the Engineer agent"""
    
    def test_initialization(self, mock_env_vars):
        """Test that the Engineer agent initializes correctly"""
        # Import Agent class using the same approach to avoid 'lambda' keyword
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../lambda/layers/common/python'))
        with patch('action_group.bizdev.engineer.index.Agent.__init__') as mock_init:
            mock_init.return_value = None  # Ensure __init__ doesn't do anything
            engineer = Engineer(TEST_AGENT_ID)
            # Check that __init__ was called with the agent_id and agent_type
            assert mock_init.call_args.kwargs['agent_id'] == TEST_AGENT_ID
            assert mock_init.call_args.kwargs['agent_type'] == "engineer"
    
    def test_implement_code_basic(self, engineer_agent):
        """Test the basic functionality of implement_code method"""
        # Mock the LLM response
        engineer_agent.ask_llm.return_value = {
            "content": "Sample code implementation"
        }
        
        # Mock the S3 upload
        engineer_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Create input data
        input_data = {
            "requirement": TEST_REQUIREMENT,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID
        }
        
        # Call the method
        result = engineer_agent.implement_code(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        assert "implementation_id" in result
        assert result["implementation"] == "Sample code implementation"
        assert result["s3_key"] == TEST_S3_KEY
        
        # Verify LLM was called with correct messages
        engineer_agent.ask_llm.assert_called_once()
        call_args = engineer_agent.ask_llm.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"
        assert TEST_REQUIREMENT in call_args[1]["content"]
        
        # Verify artifact was uploaded
        engineer_agent.artifacts.upload_artifact.assert_called_once()
        
        # Verify state was updated
        engineer_agent.add_to_memory.assert_called_once()
        engineer_agent.save_state.assert_called_once()
        
        # Verify event was emitted
        engineer_agent.emit_event.assert_called_once()
    
    def test_implement_code_with_prd_and_architecture(self, engineer_agent):
        """Test implement_code with PRD and architecture included"""
        # Mock the LLM response
        engineer_agent.ask_llm.return_value = {
            "content": "Sample code implementation"
        }
        
        # Mock the S3 upload
        engineer_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the PRD and architecture download
        engineer_agent.artifacts.download_artifact.side_effect = [
            {"prd": "Sample PRD content"},
            {"architecture": "Sample architecture content"}
        ]
        
        # Create input data with PRD ID and architecture ID
        input_data = {
            "requirement": TEST_REQUIREMENT,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID,
            "prd_id": TEST_PRD_ID,
            "architecture_id": TEST_ARCHITECTURE_ID
        }
        
        # Call the method
        result = engineer_agent.implement_code(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        
        # Verify PRD and architecture were downloaded
        assert engineer_agent.artifacts.download_artifact.call_count == 2
        
        # Verify LLM was called with PRD and architecture content
        call_args = engineer_agent.ask_llm.call_args[0][0]
        assert "PRD:" in call_args[1]["content"]
        assert "Sample PRD content" in call_args[1]["content"]
        assert "Architecture:" in call_args[1]["content"]
        assert "Sample architecture content" in call_args[1]["content"]
    
    def test_implement_code_validation(self, engineer_agent):
        """Test input validation in implement_code"""
        # Create input data without requirement
        input_data = {
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID
        }
        
        # Call the method and expect an error
        with pytest.raises(ValueError, match="Requirement is required"):
            engineer_agent.implement_code(input_data)
    
    def test_review_code(self, engineer_agent):
        """Test the review_code method"""
        # Mock the LLM response
        engineer_agent.ask_llm.return_value = {
            "content": "Sample code review"
        }
        
        # Mock the S3 upload
        engineer_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the implementation download
        engineer_agent.artifacts.download_artifact.return_value = {
            "implementation": "Sample implementation code",
            "requirement": TEST_REQUIREMENT
        }
        
        # Create input data
        input_data = {
            "implementation_id": TEST_IMPLEMENTATION_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID
        }
        
        # Call the method
        result = engineer_agent.review_code(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        assert "review_id" in result
        assert result["review"] == "Sample code review"
        assert result["s3_key"] == TEST_S3_KEY
        
        # Verify implementation was downloaded
        engineer_agent.artifacts.download_artifact.assert_called_once_with(
            project_id=TEST_PROJECT_ID,
            agent_type="engineer",
            artifact_type="implementation",
            artifact_id=TEST_IMPLEMENTATION_ID,
            timestamp=TEST_TIMESTAMP
        )
        
        # Verify LLM was called with correct messages
        engineer_agent.ask_llm.assert_called_once()
        call_args = engineer_agent.ask_llm.call_args[0][0]
        assert "Sample implementation code" in call_args[1]["content"]
        
        # Verify state was updated
        engineer_agent.add_to_memory.assert_called_once()
        engineer_agent.save_state.assert_called_once()
        
        # Verify event was emitted
        engineer_agent.emit_event.assert_called_once()
    
    def test_review_code_validation(self, engineer_agent):
        """Test input validation in review_code"""
        # Test missing implementation_id
        input_data = {
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP
        }
        
        with pytest.raises(ValueError, match="Implementation ID is required"):
            engineer_agent.review_code(input_data)
        
        # Test missing project_id
        input_data = {
            "implementation_id": TEST_IMPLEMENTATION_ID,
            "timestamp": TEST_TIMESTAMP
        }
        
        with pytest.raises(ValueError, match="Project ID is required"):
            engineer_agent.review_code(input_data)
    
    def test_fix_bugs(self, engineer_agent):
        """Test the fix_bugs method"""
        # Mock the LLM response
        engineer_agent.ask_llm.return_value = {
            "content": "Sample fixed code"
        }
        
        # Mock the S3 upload
        engineer_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the implementation and review download
        engineer_agent.artifacts.download_artifact.side_effect = [
            {
                "implementation": "Sample implementation code",
                "requirement": TEST_REQUIREMENT
            },
            {
                "review": "Sample review content"
            }
        ]
        
        # Create input data
        input_data = {
            "implementation_id": TEST_IMPLEMENTATION_ID,
            "review_id": TEST_REVIEW_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID
        }
        
        # Call the method
        result = engineer_agent.fix_bugs(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        assert "fixed_id" in result
        assert result["fixed_implementation"] == "Sample fixed code"
        assert result["s3_key"] == TEST_S3_KEY
        
        # Verify implementation and review were downloaded
        assert engineer_agent.artifacts.download_artifact.call_count == 2
        
        # Verify LLM was called with correct messages
        engineer_agent.ask_llm.assert_called_once()
        call_args = engineer_agent.ask_llm.call_args[0][0]
        assert "Sample implementation code" in call_args[1]["content"]
        assert "Sample review content" in call_args[1]["content"]
        
        # Verify state was updated
        engineer_agent.add_to_memory.assert_called_once()
        engineer_agent.save_state.assert_called_once()
        
        # Verify event was emitted
        engineer_agent.emit_event.assert_called_once()
    
    def test_fix_bugs_without_review(self, engineer_agent):
        """Test fix_bugs without a review"""
        # Mock the LLM response
        engineer_agent.ask_llm.return_value = {
            "content": "Sample fixed code"
        }
        
        # Mock the S3 upload
        engineer_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the implementation download
        engineer_agent.artifacts.download_artifact.return_value = {
            "implementation": "Sample implementation code",
            "requirement": TEST_REQUIREMENT
        }
        
        # Create input data without review_id
        input_data = {
            "implementation_id": TEST_IMPLEMENTATION_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID
        }
        
        # Call the method
        result = engineer_agent.fix_bugs(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        
        # Verify only implementation was downloaded (no review)
        engineer_agent.artifacts.download_artifact.assert_called_once()
        
        # Verify LLM was called with empty review
        call_args = engineer_agent.ask_llm.call_args[0][0]
        assert "Review:\n" in call_args[1]["content"]
    
    def test_process_method_routing(self, engineer_agent):
        """Test that the process method routes to the correct method"""
        # Mock the individual methods
        engineer_agent.implement_code = MagicMock(return_value={"status": "success"})
        engineer_agent.review_code = MagicMock(return_value={"status": "success"})
        engineer_agent.fix_bugs = MagicMock(return_value={"status": "success"})
        
        # Test implement_code routing
        input_data = {"process_type": "implement_code"}
        engineer_agent.process(input_data)
        engineer_agent.implement_code.assert_called_once_with(input_data)
        
        # Test review_code routing
        input_data = {"process_type": "review_code"}
        engineer_agent.process(input_data)
        engineer_agent.review_code.assert_called_once_with(input_data)
        
        # Test fix_bugs routing
        input_data = {"process_type": "fix_bugs"}
        engineer_agent.process(input_data)
        engineer_agent.fix_bugs.assert_called_once_with(input_data)
        
        # Test unknown process type
        input_data = {"process_type": "unknown_type"}
        result = engineer_agent.process(input_data)
        assert result["status"] == "failed"
        assert "Unknown process type" in result["error"]
    
    def test_error_handling(self, engineer_agent):
        """Test error handling in the methods"""
        # Mock the implementation download to raise an exception
        engineer_agent.artifacts.download_artifact.side_effect = Exception("Download failed")
        
        # Create input data
        input_data = {
            "implementation_id": TEST_IMPLEMENTATION_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP
        }
        
        # Call the method and expect an error
        with pytest.raises(ValueError, match="Failed to load implementation"):
            engineer_agent.review_code(input_data)
