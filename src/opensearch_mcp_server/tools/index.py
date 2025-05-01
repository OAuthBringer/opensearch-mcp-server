import logging
from typing import Dict, Any
from ..es_client import OpensearchClient
from mcp.types import TextContent

class IndexTools(OpensearchClient):
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
