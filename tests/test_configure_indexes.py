import pytest
import os
import tempfile
import yaml
from pathlib import Path
from mcp.types import TextContent
from typing import AsyncGenerator
from opensearch_mcp_server.tools.index import IndexTools

# Import necessary dependencies for mocking OpenSearch
import unittest.mock as mock


@pytest.fixture
async def index_tools() -> AsyncGenerator:
    """Create an IndexTools instance for testing."""
    # Create a logger mock
    logger_mock = mock.MagicMock()
    
    # Create the IndexTools instance
    tools = IndexTools(logger_mock)
    yield tools


@pytest.fixture
def test_config_dir() -> str:
    """Create a temporary directory with test index configurations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test YAML file in the temporary directory
        test_index_path = Path(temp_dir) / "test_index.yaml"
        test_config = {
            "index_name": "test_index_fixture",
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                }
            }
        }
        
        with open(test_index_path, 'w') as f:
            yaml.dump(test_config, f)
            
        yield temp_dir


@pytest.mark.asyncio
async def test_configure_indexes(index_tools, test_config_dir):
    """Test the configure_indexes tool."""
    # Mock the OpenSearch client's index_exists and indices.create methods
    with mock.patch.object(index_tools, 'es_client') as mock_client:
        # Configure the mock
        mock_client.indices.exists.return_value = False  # Index doesn't exist yet
        mock_client.indices.create.return_value = {"acknowledged": True}
        
        # Call the configure_indexes function directly
        result = await index_tools.register_tools.configure_indexes(config_dir=test_config_dir)
        
        # Verify the result format
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        
        # Convert result to dictionary for easier assertions
        import ast
        result_dict = ast.literal_eval(result[0].text)
        
        # Assert expected results
        assert result_dict["scanned"] == 1
        assert result_dict["created"] == 1
        assert result_dict["errors"] == 0
        assert len(result_dict["details"]) == 1
        assert result_dict["details"][0]["index"] == "test_index_fixture"
        assert result_dict["details"][0]["action"] == "created"
        assert result_dict["details"][0]["status"] == "success"
        
        # Verify that the mock methods were called with expected arguments
        mock_client.indices.exists.assert_called_once_with(index="test_index_fixture")
        
        # Check that create was called with proper body
        create_call = mock_client.indices.create.call_args
        assert create_call[1]["index"] == "test_index_fixture"
        assert "settings" in create_call[1]["body"]
        assert "mappings" in create_call[1]["body"]


@pytest.mark.asyncio
async def test_configure_indexes_existing_index(server, test_config_dir):
    """Test configure_indexes when the index already exists."""
    # Mock the OpenSearch client's methods
    with mock.patch('opensearch_mcp_server.tools.index.IndexTools.es_client') as mock_client:
        # Configure the mock - index already exists
        mock_client.indices.exists.return_value = True
        
        async with Client(server) as client:
            # Call the configure_indexes tool
            result = await client.call_tool("configure_indexes", {
                "config_dir": test_config_dir
            })
            
            # Verify the result
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Convert result to dictionary
            import ast
            result_dict = ast.literal_eval(result[0].text)
            
            # Assert expected results
            assert result_dict["scanned"] == 1
            assert result_dict["created"] == 0
            assert result_dict["already_exists"] == 1
            assert result_dict["errors"] == 0
            assert len(result_dict["details"]) == 1
            assert result_dict["details"][0]["index"] == "test_index_fixture"
            assert result_dict["details"][0]["action"] == "skipped"
            assert result_dict["details"][0]["status"] == "already_exists"
            
            # Verify that indices.create was not called
            mock_client.indices.create.assert_not_called()


@pytest.mark.asyncio
async def test_configure_indexes_nonexistent_dir(server):
    """Test configure_indexes with a directory that doesn't exist."""
    with mock.patch('opensearch_mcp_server.tools.index.IndexTools.es_client') as mock_client:
        async with Client(server) as client:
            # Call with a nonexistent directory
            result = await client.call_tool("configure_indexes", {
                "config_dir": "/path/that/does/not/exist"
            })
            
            # Verify error response
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Error: Configuration directory '/path/that/does/not/exist' does not exist" in result[0].text
            
            # Verify no OpenSearch calls were made
            mock_client.indices.exists.assert_not_called()
            mock_client.indices.create.assert_not_called()


@pytest.mark.asyncio
async def test_configure_indexes_empty_dir(server):
    """Test configure_indexes with an empty directory."""
    with tempfile.TemporaryDirectory() as empty_dir:
        with mock.patch('opensearch_mcp_server.tools.index.IndexTools.es_client') as mock_client:
            async with Client(server) as client:
                # Call with an empty directory
                result = await client.call_tool("configure_indexes", {
                    "config_dir": empty_dir
                })
                
                # Verify response
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert f"No index configuration files found in '{empty_dir}'" in result[0].text
                
                # Verify no OpenSearch calls were made
                mock_client.indices.exists.assert_not_called()
                mock_client.indices.create.assert_not_called()


@pytest.mark.asyncio
async def test_configure_indexes_invalid_yaml(server):
    """Test configure_indexes with invalid YAML file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create an invalid YAML file
        invalid_yaml_path = Path(temp_dir) / "invalid.yaml"
        with open(invalid_yaml_path, 'w') as f:
            f.write("This is not valid YAML content")
        
        with mock.patch('opensearch_mcp_server.tools.index.IndexTools.es_client') as mock_client:
            async with Client(server) as client:
                # Call with directory containing invalid YAML
                result = await client.call_tool("configure_indexes", {
                    "config_dir": temp_dir
                })
                
                # Verify result indicates error
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                
                import ast
                result_dict = ast.literal_eval(result[0].text)
                
                assert result_dict["scanned"] == 1
                assert result_dict["errors"] == 1
                assert len(result_dict["details"]) == 1
                assert result_dict["details"][0]["status"] == "error"
                
                # Verify no OpenSearch calls were made
                mock_client.indices.exists.assert_not_called()
                mock_client.indices.create.assert_not_called()
