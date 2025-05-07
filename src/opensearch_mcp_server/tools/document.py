import logging
import uuid
from typing import Dict, Any
from ..es_client import OpensearchClient
from mcp.types import TextContent

class DocumentTools(OpensearchClient):
    def register_tools(self, mcp: Any):
        """Register document-related tools."""
        
        @mcp.tool(description="Search documents in an index with a custom query")
        async def search_documents(index: str, body: dict) -> list[TextContent]:
            """
            Search documents in a specified index using a custom query.
            
            Args:
                index: Name of the index to search
                body: Opensearch query DSL
            """
            self.logger.info(f"Searching in index: {index} with query: {body}")
            try:
                response = self.es_client.search(index=index, body=body)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error searching documents: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Index a document into an index")
        async def index_document(index: str, id: str, body: dict) -> list[TextContent]:
            """
            Index a document into a specified index.

            Args:
                index: Name of the index
                id: Document ID
                body: Document content
            """
            self.logger.info(f"Indexing document in index: {index} with ID: {id} and body: {body}")
            try:
                response = self.es_client.index(index=index, id=id, body=body)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error indexing document: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Delete a document from an index")
        async def delete_document(index: str, id: str) -> list[TextContent]:
            """
            Delete a document from a specified index.

            Args:
                index: Name of the index
                id: Document ID
            """
            self.logger.info(f"Deleting document from index: {index} with ID: {id}")
            try:
                response = self.es_client.delete(index=index, id=id)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error deleting document: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Bulk index documents into an index")
        async def bulk_index_documents(index: str, documents: list[dict]) -> list[TextContent]:
            """
            Bulk index multiple documents into a specified index.

            Args:
                index: Name of the index
                documents: List of documents to index, each as a dictionary
            """
            self.logger.info(f"Bulk indexing documents into index: {index}")
            try:
                actions = [
                    {
                        "_index": index,
                        "_id": doc.get("id", str(uuid.uuid4())),
                        "_source": doc
                    }
                    for doc in documents
                ]
                response = self.es_client.bulk(body=actions)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error bulk indexing documents: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
