import json
import os
import sys
import pytest
import uuid
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

# Import the Architect class from the module using a different approach
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../lambda'))
from action_group.bizdev.architect.index import Architect

# Test constants
TEST_AGENT_ID = "test-architect-agent"
TEST_PROJECT_ID = "test-project-123"
TEST_REQUIREMENT = "Create a mobile app for household finance management"
TEST_ARCHITECTURE_ID = "test-arch-123"
TEST_DIAGRAM_ID = "test-diagram-123"
TEST_DESIGN_ID = "test-design-123"
TEST_TIMESTAMP = "2025-04-05T12:00:00"
TEST_USER_ID = "test-user-123"
TEST_PRD_ID = "test-prd-123"
TEST_USE_CASE = "User adds a new expense"
TEST_S3_KEY = "projects/test-project-123/architect/architecture/test-arch-123/2025-04-05T12:00:00.json"

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
        'EVENT_BUS_NAME': 'test-event-bus'
    }):
        yield

@pytest.fixture
def architect_agent(mock_env_vars):
    """Create an Architect agent for testing"""
    # Import Agent class using the same approach to avoid 'lambda' keyword
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../lambda/layers/common/python'))
    with patch('action_group.bizdev.architect.index.Agent.__init__') as mock_init:
        mock_init.return_value = None
        agent = Architect(TEST_AGENT_ID)
        
        # Mock the necessary attributes and methods
        agent.agent_id = TEST_AGENT_ID
        agent.agent_type = "architect"
        agent.state = "initialized"
        agent.memory = []
        agent.artifacts = MagicMock()
        agent.ask_llm = MagicMock()
        agent.save_state = MagicMock()
        agent.add_to_memory = MagicMock()
        agent.emit_event = MagicMock()
        agent.send_message = MagicMock()
        
        return agent

class TestArchitect:
    """Test cases for the Architect agent"""
    
    def test_initialization(self, mock_env_vars):
        """Test that the Architect agent initializes correctly"""
        # Import Agent class using the same approach to avoid 'lambda' keyword
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../../lambda/layers/common/python'))
        with patch('action_group.bizdev.architect.index.Agent.__init__') as mock_init:
            mock_init.return_value = None  # Ensure __init__ doesn't do anything
            architect = Architect(TEST_AGENT_ID)
            # Check that __init__ was called with the agent_id and agent_type
            assert mock_init.call_args.kwargs['agent_id'] == TEST_AGENT_ID
            assert mock_init.call_args.kwargs['agent_type'] == "architect"
    
    def test_create_architecture_basic(self, architect_agent):
        """Test the basic functionality of create_architecture method"""
        # Mock the LLM response
        architect_agent.ask_llm.return_value = {
            "content": "Sample architecture design content"
        }
        
        # Mock the S3 upload
        architect_agent.artifacts.upload_artifact.return_value = {
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
        result = architect_agent.create_architecture(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        assert "architecture_id" in result
        assert result["architecture"] == "Sample architecture design content"
        assert result["s3_key"] == TEST_S3_KEY
        
        # Verify LLM was called with correct messages
        architect_agent.ask_llm.assert_called_once()
        call_args = architect_agent.ask_llm.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"
        assert TEST_REQUIREMENT in call_args[1]["content"]
        
        # Verify artifact was uploaded
        architect_agent.artifacts.upload_artifact.assert_called_once()
        
        # Verify state was updated
        architect_agent.add_to_memory.assert_called_once()
        architect_agent.save_state.assert_called_once()
        
        # Verify event was emitted
        architect_agent.emit_event.assert_called_once()
        
        # Verify message was sent to engineer
        architect_agent.send_message.assert_called_once_with(
            recipient_id="engineer",
            content=ANY
        )
    
    def test_create_architecture_with_prd(self, architect_agent):
        """Test create_architecture with PRD included"""
        # Mock the LLM response
        architect_agent.ask_llm.return_value = {
            "content": "Sample architecture design content"
        }
        
        # Mock the S3 upload
        architect_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the PRD download
        architect_agent.artifacts.download_artifact.return_value = {
            "prd": "Sample PRD content"
        }
        
        # Create input data with PRD ID
        input_data = {
            "requirement": TEST_REQUIREMENT,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID,
            "prd_id": TEST_PRD_ID
        }
        
        # Call the method
        result = architect_agent.create_architecture(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        
        # Verify PRD was downloaded
        architect_agent.artifacts.download_artifact.assert_called_once_with(
            project_id=TEST_PROJECT_ID,
            agent_type="product_manager",
            artifact_type="prd",
            artifact_id=TEST_PRD_ID,
            timestamp=TEST_TIMESTAMP
        )
        
        # Verify LLM was called with PRD content
        call_args = architect_agent.ask_llm.call_args[0][0]
        assert "PRD:" in call_args[1]["content"]
        assert "Sample PRD content" in call_args[1]["content"]
    
    def test_create_architecture_validation(self, architect_agent):
        """Test input validation in create_architecture"""
        # Create input data without requirement
        input_data = {
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "user_id": TEST_USER_ID
        }
        
        # Call the method and expect an error
        with pytest.raises(ValueError, match="Requirement is required"):
            architect_agent.create_architecture(input_data)
    
    def test_create_class_diagram(self, architect_agent):
        """Test the create_class_diagram method"""
        # Mock the LLM response
        architect_agent.ask_llm.return_value = {
            "content": "Sample class diagram content"
        }
        
        # Mock the S3 upload
        architect_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the architecture download
        architect_agent.artifacts.download_artifact.return_value = {
            "architecture": "Sample architecture content",
            "requirement": TEST_REQUIREMENT
        }
        
        # Create input data
        input_data = {
            "architecture_id": TEST_ARCHITECTURE_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP
        }
        
        # Call the method
        result = architect_agent.create_class_diagram(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        assert "diagram_id" in result
        assert result["class_diagram"] == "Sample class diagram content"
        assert result["s3_key"] == TEST_S3_KEY
        
        # Verify architecture was downloaded
        architect_agent.artifacts.download_artifact.assert_called_once_with(
            project_id=TEST_PROJECT_ID,
            agent_type="architect",
            artifact_type="architecture",
            artifact_id=TEST_ARCHITECTURE_ID,
            timestamp=TEST_TIMESTAMP
        )
        
        # Verify LLM was called with correct messages
        architect_agent.ask_llm.assert_called_once()
        call_args = architect_agent.ask_llm.call_args[0][0]
        assert "Sample architecture content" in call_args[1]["content"]
        
        # Verify state was updated
        architect_agent.add_to_memory.assert_called_once()
        architect_agent.save_state.assert_called_once()
    
    def test_create_sequence_diagram(self, architect_agent):
        """Test the create_sequence_diagram method"""
        # Mock the LLM response
        architect_agent.ask_llm.return_value = {
            "content": "Sample sequence diagram content"
        }
        
        # Mock the S3 upload
        architect_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the architecture download
        architect_agent.artifacts.download_artifact.return_value = {
            "architecture": "Sample architecture content",
            "requirement": TEST_REQUIREMENT
        }
        
        # Create input data
        input_data = {
            "architecture_id": TEST_ARCHITECTURE_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "use_case": TEST_USE_CASE
        }
        
        # Call the method
        result = architect_agent.create_sequence_diagram(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        assert "diagram_id" in result
        assert result["sequence_diagram"] == "Sample sequence diagram content"
        assert result["s3_key"] == TEST_S3_KEY
        
        # Verify architecture was downloaded
        architect_agent.artifacts.download_artifact.assert_called_once_with(
            project_id=TEST_PROJECT_ID,
            agent_type="architect",
            artifact_type="architecture",
            artifact_id=TEST_ARCHITECTURE_ID,
            timestamp=TEST_TIMESTAMP
        )
        
        # Verify LLM was called with correct messages
        architect_agent.ask_llm.assert_called_once()
        call_args = architect_agent.ask_llm.call_args[0][0]
        assert TEST_USE_CASE in call_args[1]["content"]
        
        # Verify state was updated
        architect_agent.add_to_memory.assert_called_once()
        architect_agent.save_state.assert_called_once()
    
    def test_create_api_design(self, architect_agent):
        """Test the create_api_design method"""
        # Mock the LLM response
        architect_agent.ask_llm.return_value = {
            "content": "Sample API design content"
        }
        
        # Mock the S3 upload
        architect_agent.artifacts.upload_artifact.return_value = {
            "s3_key": TEST_S3_KEY
        }
        
        # Mock the architecture download
        architect_agent.artifacts.download_artifact.return_value = {
            "architecture": "Sample architecture content",
            "requirement": TEST_REQUIREMENT
        }
        
        # Create input data
        input_data = {
            "architecture_id": TEST_ARCHITECTURE_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP
        }
        
        # Call the method
        result = architect_agent.create_api_design(input_data)
        
        # Verify the result
        assert result["status"] == "success"
        assert "design_id" in result
        assert result["api_design"] == "Sample API design content"
        assert result["s3_key"] == TEST_S3_KEY
        
        # Verify architecture was downloaded
        architect_agent.artifacts.download_artifact.assert_called_once_with(
            project_id=TEST_PROJECT_ID,
            agent_type="architect",
            artifact_type="architecture",
            artifact_id=TEST_ARCHITECTURE_ID,
            timestamp=TEST_TIMESTAMP
        )
        
        # Verify LLM was called with correct messages
        architect_agent.ask_llm.assert_called_once()
        call_args = architect_agent.ask_llm.call_args[0][0]
        assert "Sample architecture content" in call_args[1]["content"]
        
        # Verify state was updated
        architect_agent.add_to_memory.assert_called_once()
        architect_agent.save_state.assert_called_once()
    
    def test_process_method_routing(self, architect_agent):
        """Test that the process method routes to the correct method"""
        # Mock the individual methods
        architect_agent.create_architecture = MagicMock(return_value={"status": "success"})
        architect_agent.create_class_diagram = MagicMock(return_value={"status": "success"})
        architect_agent.create_sequence_diagram = MagicMock(return_value={"status": "success"})
        architect_agent.create_api_design = MagicMock(return_value={"status": "success"})
        
        # Test create_architecture routing
        input_data = {"process_type": "create_architecture"}
        architect_agent.process(input_data)
        architect_agent.create_architecture.assert_called_once_with(input_data)
        
        # Test create_class_diagram routing
        input_data = {"process_type": "create_class_diagram"}
        architect_agent.process(input_data)
        architect_agent.create_class_diagram.assert_called_once_with(input_data)
        
        # Test create_sequence_diagram routing
        input_data = {"process_type": "create_sequence_diagram"}
        architect_agent.process(input_data)
        architect_agent.create_sequence_diagram.assert_called_once_with(input_data)
        
        # Test create_api_design routing
        input_data = {"process_type": "create_api_design"}
        architect_agent.process(input_data)
        architect_agent.create_api_design.assert_called_once_with(input_data)
        
        # Test unknown process type
        input_data = {"process_type": "unknown_type"}
        with pytest.raises(ValueError, match="Unknown process type"):
            architect_agent.process(input_data)
    
    def test_error_handling(self, architect_agent):
        """Test error handling in the methods"""
        # Mock the architecture download to raise an exception
        architect_agent.artifacts.download_artifact.side_effect = Exception("Download failed")
        
        # Create input data
        input_data = {
            "architecture_id": TEST_ARCHITECTURE_ID,
            "project_id": TEST_PROJECT_ID,
            "timestamp": TEST_TIMESTAMP,
            "use_case": TEST_USE_CASE
        }
        
        # Call the method and expect an error
        with pytest.raises(ValueError, match="Failed to load architecture"):
            architect_agent.create_sequence_diagram(input_data)
