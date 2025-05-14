import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..es_client import OpensearchClient
from mcp.types import TextContent

class IndexTools(OpensearchClient):
    DEFAULT_CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "configs/indices"))
    def register_tools(self, mcp: Any):
        """Register index-related tools."""
        
        @mcp.tool(description="List all indices in the Opensearch cluster")
        async def list_indices() -> list[TextContent]:
            """List all indices in the Opensearch cluster."""
            self.logger.info("Listing indices...")
            try:
                indices = self.es_client.cat.indices(format="json")
                return [TextContent(type="text", text=str(indices))]
            except Exception as e:
                self.logger.error(f"Error listing indices: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Get index mapping")
        async def get_mapping(index: str) -> list[TextContent]:
            """
            Get the mapping for an index.
            
            Args:
                index: Name of the index
            """
            self.logger.info(f"Getting mapping for index: {index}")
            try:
                response = self.es_client.indices.get_mapping(index=index)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error getting mapping: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Get index settings")
        async def get_settings(index: str) -> list[TextContent]:
            """
            Get the settings for an index.
            
            Args:
                index: Name of the index
            """
            self.logger.info(f"Getting settings for index: {index}")
            try:
                response = self.es_client.indices.get_settings(index=index)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error getting settings: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Create a new index in the Opensearch cluster")
        async def create_index(index: str, body: dict) -> list[TextContent]:
            """
            Create a new index in the Opensearch cluster.

            Args:
                index: Name of the index to create
                body: Index settings and mappings
            """
            self.logger.info(f"Creating index: {index} with body: {body}")
            try:
                response = self.es_client.indices.create(index=index, body=body)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error creating index: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Delete an index from the Opensearch cluster")
        async def delete_index(index: str) -> list[TextContent]:
            """
            Delete an index from the Opensearch cluster.

            Args:
                index: Name of the index to delete
            """
            self.logger.info(f"Deleting index: {index}")
            try:
                response = self.es_client.indices.delete(index=index)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error deleting index: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @mcp.tool(description="Run index configuration job.  Will default to indexes defined locally, no parameters are needed unless specified")
        async def configure_indices(config_dir: str = None) -> list[TextContent]:
            """
            Scan a directory for YAML index configurations, compare with existing 
            indexes, and create missing indexes with appropriate mappings.
            
            Args:
                config_dir: Optional directory path containing YAML configs (defaults to ./configs/indexes)
            """
            # Use default config directory if none provided
            config_dir = config_dir or self.DEFAULT_CONFIG_DIR
            config_path = Path(config_dir)
            self.logger.info(f"Configuring indexes from: {config_path}")
            
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
                        index_exists = self.es_client.indices.exists(index=index_name)
                        
                        detail = {
                            "file": str(yaml_file),
                            "index": index_name,
                            "action": None,
                            "status": None
                        }
                        
                        if not index_exists:
                            # Create the index
                            self.logger.info(f"Creating index '{index_name}' from {yaml_file}")
                            response = self.es_client.indices.create(index=index_name, body=body)
                            detail["action"] = "created"
                            detail["status"] = "success"
                            results["created"] += 1
                        else:
                            self.logger.info(f"Index '{index_name}' already exists, skipping")
                            detail["action"] = "skipped"
                            detail["status"] = "already_exists"
                            results["already_exists"] += 1
                        
                        results["details"].append(detail)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing {yaml_file}: {e}")
                        results["errors"] += 1
                        results["details"].append({
                            "file": str(yaml_file),
                            "error": str(e),
                            "status": "error"
                        })
                
                return [TextContent(type="text", text=str(results))]
                
            except Exception as e:
                self.logger.error(f"Error configuring indexes: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
