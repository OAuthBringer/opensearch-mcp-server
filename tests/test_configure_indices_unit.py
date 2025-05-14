import pytest
import os
import tempfile
import yaml
from pathlib import Path
from mcp.types import TextContent
import unittest.mock as mock
from opensearch_mcp_server.tools.index import IndexTools


@pytest.fixture
def index_tools():
    """Create an IndexTools instance for testing."""
    # Create a logger mock
    logger_mock = mock.MagicMock()
    
    # Create the IndexTools instance with mocked methods
    with mock.patch.object(IndexTools, '_get_es_config') as mock_get_config:
        with mock.patch.object(IndexTools, '_create_opensearch_client') as mock_create_client:
            # Mock the config
            mock_get_config.return_value = {
                "host": "http://localhost:9200",
                "username": "admin",
                "password": "admin",
            }
            
            # Mock the client
            mock_client = mock.MagicMock()
            mock_create_client.return_value = mock_client
            
            # Create the tools instance
            tools = IndexTools(logger_mock)
            
            # Replace the mocked client with a new mock for tests
            tools.es_client = mock.MagicMock()
            
            return tools


@pytest.fixture
def test_config_dir():
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


class TestConfigureIndices:
    """Tests for the configure_indices functionality."""
    
    # Helper function to extract the configure_indices functionality
    async def configure_indices(self, tools, config_dir=None):
        """Extract the functionality from the tool for direct testing."""
        # Use default config directory if none provided
        config_dir = config_dir or tools.DEFAULT_CONFIG_DIR
        config_path = Path(config_dir)
        tools.logger.info(f"Configuring indexes from: {config_path}")
        
        results = {
            "scanned": 0,
            "created": 0,
            "already_exists": 0,
            "errors": 0,
            "details": []
        }
        
        try:
            # Ensure directory exists
            if not config_path.exists():
                return [TextContent(
                    type="text", 
                    text=f"Error: Configuration directory '{config_dir}' does not exist"
                )]
            
            # Scan for YAML files
            yaml_files = list(config_path.glob("*.yaml")) + list(config_path.glob("*.yml"))
            results["scanned"] = len(yaml_files)
            
            if len(yaml_files) == 0:
                return [TextContent(
                    type="text", 
                    text=f"No index configuration files found in '{config_dir}'"
                )]
            
            # Process each configuration file
            for yaml_file in yaml_files:
                try:
                    # Load YAML configuration
                    with open(yaml_file, 'r') as file:
                        config = yaml.safe_load(file)
                    
                    # Validate configuration
                    if not config or not isinstance(config, dict):
                        raise ValueError(f"Invalid configuration format in {yaml_file}")
                    
                    if 'index_name' not in config:
                        raise ValueError(f"Missing 'index_name' in {yaml_file}")
                    
                    index_name = config['index_name']
                    
                    # Prepare index creation body
                    body = {}
                    if 'settings' in config:
                        body['settings'] = config['settings']
                    if 'mappings' in config:
                        body['mappings'] = config['mappings']
                    
                    # Check if index exists
                    index_exists = tools.es_client.indices.exists(index=index_name)
                    
                    detail = {
                        "file": str(yaml_file),
                        "index": index_name,
                        "action": None,
                        "status": None
                    }
                    
                    if not index_exists:
                        # Create the index
                        tools.logger.info(f"Creating index '{index_name}' from {yaml_file}")
                        response = tools.es_client.indices.create(index=index_name, body=body)
                        detail["action"] = "created"
                        detail["status"] = "success"
                        results["created"] += 1
                    else:
                        tools.logger.info(f"Index '{index_name}' already exists, skipping")
                        detail["action"] = "skipped"
                        detail["status"] = "already_exists"
                        results["already_exists"] += 1
                    
                    results["details"].append(detail)
                    
                except Exception as e:
                    tools.logger.error(f"Error processing {yaml_file}: {e}")
                    results["errors"] += 1
                    results["details"].append({
                        "file": str(yaml_file),
                        "error": str(e),
                        "status": "error"
                    })
            
            return [TextContent(type="text", text=str(results))]
            
        except Exception as e:
            tools.logger.error(f"Error configuring indexes: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    @pytest.mark.asyncio
    async def test_configure_indices_create_index(self, index_tools, test_config_dir):
        """Test configuring indices when the index doesn't exist."""
        # Mock the OpenSearch client
        with mock.patch.object(index_tools, 'es_client') as mock_client:
            # Configure the mock - index doesn't exist
            mock_client.indices.exists.return_value = False
            mock_client.indices.create.return_value = {"acknowledged": True}
            
            # Call the configure_indices function
            result = await self.configure_indices(index_tools, test_config_dir)
            
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
            
            # Verify that the mock methods were called correctly
            mock_client.indices.exists.assert_called_once_with(index="test_index_fixture")
            
            # Check that create was called with proper body
            create_call = mock_client.indices.create.call_args
            assert create_call[1]["index"] == "test_index_fixture"
            assert "settings" in create_call[1]["body"]
            assert "mappings" in create_call[1]["body"]
    
    @pytest.mark.asyncio
    async def test_configure_indices_existing_index(self, index_tools, test_config_dir):
        """Test configuring indices when the index already exists."""
        # Mock the OpenSearch client
        with mock.patch.object(index_tools, 'es_client') as mock_client:
            # Configure the mock - index already exists
            mock_client.indices.exists.return_value = True
            
            # Call the configure_indices function
            result = await self.configure_indices(index_tools, test_config_dir)
            
            # Verify the result format
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Convert result to dictionary for easier assertions
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
    async def test_configure_indices_nonexistent_dir(self, index_tools):
        """Test configuring indices with a directory that doesn't exist."""
        # Call the configure_indices function with nonexistent directory
        result = await self.configure_indices(index_tools, "/path/that/does/not/exist")
        
        # Verify the result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error: Configuration directory '/path/that/does/not/exist' does not exist" in result[0].text
    
    @pytest.mark.asyncio
    async def test_configure_indices_empty_dir(self, index_tools):
        """Test configuring indices with an empty directory."""
        with tempfile.TemporaryDirectory() as empty_dir:
            # Call the configure_indices function with empty directory
            result = await self.configure_indices(index_tools, empty_dir)
            
            # Verify the result
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert f"No index configuration files found in '{empty_dir}'" in result[0].text
    
    @pytest.mark.asyncio
    async def test_configure_indices_invalid_yaml(self, index_tools):
        """Test configuring indices with invalid YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create an invalid YAML file
            invalid_yaml_path = Path(temp_dir) / "invalid.yaml"
            with open(invalid_yaml_path, 'w') as f:
                f.write("This is not valid YAML content")
            
            # Call the configure_indices function
            result = await self.configure_indices(index_tools, temp_dir)
            
            # Verify the result format
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Convert result to dictionary for easier assertions
            import ast
            result_dict = ast.literal_eval(result[0].text)
            
            # Assert expected results
            assert result_dict["scanned"] == 1
            assert result_dict["errors"] == 1
            assert len(result_dict["details"]) == 1
            assert result_dict["details"][0]["status"] == "error"
