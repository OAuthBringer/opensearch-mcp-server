import logging
import uuid
from typing import Dict, Any, Optional, Union, List
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
                
        @mcp.tool(description="Update a document with partial updates")
        async def update_document(index: str, id: str, body: dict, retry_on_conflict: Optional[int] = 3) -> list[TextContent]:
            """
            Update a document with partial updates without reindexing the entire document.
            
            Args:
                index: Name of the index
                id: Document ID to update
                body: A dict containing the partial document update (will be wrapped in {'doc': body})
                retry_on_conflict: Number of retries if there's a version conflict (default: 3)
            """
            self.logger.info(f"Updating document in index: {index} with ID: {id} and partial update: {body}")
            try:
                # Wrap the body in a 'doc' object as required by the update API
                update_body = {"doc": body}
                response = self.es_client.update(
                    index=index, 
                    id=id, 
                    body=update_body,
                    retry_on_conflict=retry_on_conflict
                )
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error updating document: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @mcp.tool(description="Update documents matching a query")
        async def update_by_query(index: str, query: dict, script: dict, conflicts: str = "abort") -> list[TextContent]:
            """
            Update multiple documents that match a query.
            
            Args:
                index: Name of the index
                query: Query to select documents to update
                script: Script object with 'source' and optional 'params' to perform updates
                conflicts: How to handle version conflicts ('abort' or 'proceed')
            """
            self.logger.info(f"Updating documents by query in index: {index} with query: {query} and script: {script}")
            try:
                update_body = {
                    "query": query,
                    "script": script
                }
                response = self.es_client.update_by_query(
                    index=index,
                    body=update_body,
                    conflicts=conflicts
                )
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error updating documents by query: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
                
        @mcp.tool(description="Get a document by ID")
        async def get_document(index: str, id: str) -> list[TextContent]:
            """
            Retrieve a document by its ID.
            
            Args:
                index: Name of the index
                id: Document ID
            """
            self.logger.info(f"Getting document from index: {index} with ID: {id}")
            try:
                response = self.es_client.get(index=index, id=id)
                return [TextContent(type="text", text=str(response))]
            except Exception as e:
                self.logger.error(f"Error getting document: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
