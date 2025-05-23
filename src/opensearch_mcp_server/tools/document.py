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
                response = self.es_client.update(
                    index=index, 
                    id=id, 
                    body=body,
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

        @mcp.tool(description="Get multiple documents by ID in a single request")
        async def mget_documents(docs: list[dict]) -> list[TextContent]:
            """
            Retrieve multiple documents by their IDs in a single request.
            
            Args:
                docs: List of document specifications, each containing:
                    - _index: Index name (required)
                    - _id: Document ID (required)
                    - _source: Optional source filtering (e.g., {"include": ["field1", "field2"]})
                    - routing: Optional routing value
            
            Example:
                docs=[
                    {"_index": "products", "_id": "1"},
                    {"_index": "products", "_id": "2", "_source": {"include": ["name", "price"]}},
                    {"_index": "users", "_id": "100"}
                ]
            """
            self.logger.info(f"Multi-getting {len(docs)} documents")
            try:
                # Validate input
                for doc in docs:
                    if "_index" not in doc or "_id" not in doc:
                        raise ValueError("Each document must have '_index' and '_id' fields")
                
                # Use the OpenSearch mget API
                response = self.es_client.mget(body={"docs": docs})
                
                # Process results to show which docs were found vs not found
                results = []
                for doc_result in response.get("docs", []):
                    if doc_result.get("found"):
                        results.append({
                            "_index": doc_result["_index"],
                            "_id": doc_result["_id"],
                            "found": True,
                            "_source": doc_result.get("_source", {})
                        })
                    else:
                        results.append({
                            "_index": doc_result["_index"],
                            "_id": doc_result["_id"],
                            "found": False
                        })
                
                return [TextContent(type="text", text=str({"docs": results, "total": len(results)}))]
            except Exception as e:
                self.logger.error(f"Error multi-getting documents: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")] 

        # Alternative: Add a simpler version that takes index + list of IDs
        @mcp.tool(description="Get multiple documents from the same index by their IDs")
        async def mget_from_index(index: str, ids: list[str], source_fields: Optional[list[str]] = None) -> list[TextContent]:
            """
            Retrieve multiple documents from a single index by their IDs.
            
            Args:
                index: Name of the index
                ids: List of document IDs to retrieve
                source_fields: Optional list of fields to include in response
            
            Example:
                index="products", ids=["1", "2", "3"], source_fields=["name", "price"]
            """
            self.logger.info(f"Multi-getting {len(ids)} documents from index: {index}")
            try:
                # Build the docs array for mget
                docs = []
                for doc_id in ids:
                    doc_spec = {"_index": index, "_id": doc_id}
                    if source_fields:
                        doc_spec["_source"] = source_fields
                    docs.append(doc_spec)
                
                response = self.es_client.mget(body={"docs": docs})
                
                # Extract just the sources for found documents
                results = []
                not_found = []
                for doc_result in response.get("docs", []):
                    if doc_result.get("found"):
                        results.append({
                            "_id": doc_result["_id"],
                            "_source": doc_result.get("_source", {})
                        })
                    else:
                        not_found.append(doc_result["_id"])
                
                return [TextContent(type="text", text=str({
                    "found": results,
                    "not_found": not_found,
                    "total_requested": len(ids),
                    "total_found": len(results)
                }))]
            except Exception as e:
                self.logger.error(f"Error multi-getting documents from index: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Execute multiple search queries in a single request")
        async def msearch_documents(searches: list[dict]) -> list[TextContent]:
            """
            Execute multiple search queries in a single request.
            
            Args:
                searches: List of search specifications, each containing:
                    - index: Index name(s) to search (required)
                    - query: Search query using OpenSearch Query DSL (required)
                    - size: Number of results to return (optional, default 10)
                    - from: Starting offset for pagination (optional, default 0)
                    - source: Source fields to include/exclude (optional)
                    - sort: Sort order (optional)
            
            Example:
                searches=[
                    {
                        "index": "products",
                        "query": {"match": {"name": "laptop"}},
                        "size": 5
                    },
                    {
                        "index": "users",
                        "query": {"term": {"status": "active"}},
                        "source": ["name", "email"],
                        "sort": [{"created_at": "desc"}]
                    }
                ]
            """
            self.logger.info(f"Executing {len(searches)} search queries")
            try:
                # Build the msearch body (alternating header/body lines)
                body = []
                for search in searches:
                    # Header line
                    header = {"index": search.get("index")}
                    body.append(header)
                    
                    # Query body line
                    query_body = {"query": search.get("query", {"match_all": {}})}
                    
                    # Add optional parameters
                    if "size" in search:
                        query_body["size"] = search["size"]
                    if "from" in search:
                        query_body["from"] = search["from"]
                    if "source" in search:
                        query_body["_source"] = search["source"]
                    if "sort" in search:
                        query_body["sort"] = search["sort"]
                        
                    body.append(query_body)
                
                # Execute msearch
                response = self.es_client.msearch(body=body)
                
                # Process results
                results = []
                for i, search_response in enumerate(response.get("responses", [])):
                    if "error" in search_response:
                        results.append({
                            "search_index": i,
                            "error": search_response["error"]
                        })
                    else:
                        hits = search_response.get("hits", {})
                        results.append({
                            "search_index": i,
                            "total": hits.get("total", {}).get("value", 0),
                            "hits": [hit["_source"] for hit in hits.get("hits", [])],
                            "took": search_response.get("took", 0)
                        })
                
                return [TextContent(type="text", text=str({
                    "results": results,
                    "total_searches": len(searches),
                    "total_time": response.get("took", 0)
                }))]
            except Exception as e:
                self.logger.error(f"Error executing multi-search: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
