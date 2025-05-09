# src/opensearch_mcp_server/tools/memory.py
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..es_client import OpensearchClient
from mcp.types import TextContent
import re

class MemoryTools(OpensearchClient):
    """Tools for managing various types of memory and context."""
    
    def __init__(self, logger: logging.Logger):
        super().__init__(logger)
        self._ensure_indices()
    
    def _ensure_indices(self):
        """Ensure required indices exist with appropriate mappings."""
        index_name = "context_store"
        
        if not self.es_client.indices.exists(index=index_name):
            self.logger.info(f"Creating index: {index_name}")
            self.es_client.indices.create(index=index_name, body=self._get_context_mapping())

    def _get_timestamp_info(self):
        """
        Generate a consistent timestamp for both ID and document creation.
        
        Returns:
            tuple: (timestamp object, formatted string for ID)
        """
        timestamp = datetime.now()
        formatted_timestamp = timestamp.strftime('%Y%m%dT%H-%M')
        return timestamp, formatted_timestamp    

    def _get_context_mapping(self):
        """Get mapping for unified context store."""
        return {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "title": {"type": "text"},
                    "content": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "keyword"},
                            "format": {"type": "keyword"},
                            "language": {"type": "keyword"},
                            # Add other metadata fields as needed
                        }
                    },
                    "key_points": {"type": "text"},  # Optional for sessions
                    "next_steps": {"type": "text"},  # Optional for sessions
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
    
    def register_tools(self, mcp: Any):
        """Register memory-related tools."""

        @mcp.tool(description="Initialize and verify memory system state WITHOUT LOGGING. NEVER follow this with store_log.")
        async def initialize_memory_system() -> list[TextContent]:
            """
            Perform all necessary checks to verify the memory system is working correctly.
            This tool COMPLETELY REPLACES any need to log initialization status.
            
            IMPORTANT: This tool itself records all needed initialization state.
            
            Examples:
                ✅ User types "init" → AI uses initialize_memory_system ONLY
                ✅ User asks about system status → AI uses initialize_memory_system
                ❌ AI follows this with any logging attempt
            """
            try:
                # Check cluster health
                health = self.es_client.cluster.health()
                
                # Get index status
                indices = self.es_client.indices.get("context_store")
                
                # Check document count
                stats = self.es_client.indices.stats(index="context_store")
                
                # Get consistent timestamp
                timestamp, _ = self._get_timestamp_info()
                
                # Format a detailed status report
                status_report = {
                    "cluster_health": health["status"],
                    "indices": list(indices.keys()),
                    "document_count": stats["_all"]["primaries"]["docs"]["count"],
                    "initialization_timestamp": timestamp.isoformat(),
                    "status": "INITIALIZATION COMPLETE - DO NOT LOG THIS EVENT, DO NOT PASS GO, DO NOT COLLECT $200"
                }
                
                return [TextContent(type="text", text=str(status_report))]
            except Exception as e:
                self.logger.error(f"Error initializing memory system: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        @mcp.tool(description="Store a session summary with key points and next steps. AI and Human use allowed, but should be performed sparingly and usually when prompted.")
        async def store_session(title: str, content: str, key_points: List[str] = None, 
                                next_steps: List[str] = None, tags: List[str] = None) -> list[TextContent]:
            """
            Store a session summary with key points and next steps.
            
            Args:
                title: Title of the session
                content: Main content or summary
                key_points: List of key points from the session
                next_steps: List of next steps or action items
                tags: Tags for categorizing and searching
            """
            self.logger.info(f"Storing session: {title}")
            try:
                # Get consistent timestamp information - SINGLE SOURCE OF TRUTH
                timestamp, formatted_timestamp = self._get_timestamp_info()
                
                # Check if title contains a timestamp pattern
                if title and re.search(r'\d{8}T\d{2}-\d{2}', title):
                    self.logger.warning(f"Title contains timestamp-like pattern: {title}")
                
                # Use our revolutionary timestamp concept consistently
                doc_id = f"session_{formatted_timestamp}_{self._slugify(title)}"
                
                doc = {
                    "id": doc_id,
                    "type": "session",
                    "title": title,
                    "content": content,
                    "key_points": key_points or [],
                    "next_steps": next_steps or [],
                    "tags": tags or [],
                    "created_at": timestamp.isoformat(),  # Same timestamp object
                    "metadata": {
                        "source": "user_session",
                        "format": "text"
                    }
                }
                
                result = self.es_client.index(
                    index="context_store",
                    body=doc,
                    id=doc_id
                )
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                self.logger.error(f"Error storing session: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]        

        @mcp.tool(description="Store a quick log entry or note - PRIMARILY FOR HUMAN USE, AI should avoid using unless explicitly instructed")
        async def store_log(content: str, title: str = None, tags: List[str] = None) -> list[TextContent]:
            """
            Store a quick log entry or note. This tool is primarily intended for human users to record their thoughts and observations.
            AIs should rarely use this tool unprompted - wait for explicit human direction.
            
            Examples:
                ✅ Human: "Log this insight about distributed systems"
                ✅ Human: "store log | We discussed an important architecture decision today"
                ✅ Human: "Please create a log of today's meeting"
                ❌ AI using log without explicit instruction
                ❌ AI automatically logging every insight or observation

            Args:
                content: The log content
                title: Optional title (defaults to truncated content)
                tags: Tags for categorizing and searching
            """
            # Create title from content if not provided
            if not title:
                title = content[:50] + ('...' if len(content) > 50 else '')
                
            self.logger.info(f"Storing log: {title}")
            
            try:
                # Get consistent timestamp information - SINGLE SOURCE OF TRUTH
                timestamp, formatted_timestamp = self._get_timestamp_info()
                
                # Check if title contains a timestamp pattern
                if title and re.search(r'\d{8}T\d{2}-\d{2}', title):
                    self.logger.warning(f"Title contains timestamp-like pattern: {title}")
                
                # Use the SAME timestamp values throughout
                doc_id = f"log_{formatted_timestamp}_{uuid.uuid4().hex[:8]}"
                
                doc = {
                    "id": doc_id,
                    "type": "log",
                    "title": title,
                    "content": content,
                    "tags": tags or [],
                    "created_at": timestamp.isoformat(),  # Same timestamp object used here
                    "metadata": {
                        "source": "user_log",
                        "format": "text"
                    }
                }
                
                result = self.es_client.index(
                    index="context_store",
                    body=doc,
                    id=doc_id
                )
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                self.logger.error(f"Error storing log: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]        

        @mcp.tool(description="Store reference material like documentation or research")
        async def store_reference(title: str, content: str, source: str = None, 
                                 tags: List[str] = None) -> list[TextContent]:
            """
            Store reference material like documentation or research.
            
            Args:
                title: Title of the reference
                content: The reference content
                source: Source of the reference (e.g., website, book)
                tags: Tags for categorizing and searching
            """
            self.logger.info(f"Storing reference: {title}")
            try:
                # Get consistent timestamp information 
                timestamp, formatted_timestamp = self._get_timestamp_info()
                
                # Check if title contains a timestamp pattern
                if title and re.search(r'\d{8}T\d{2}-\d{2}', title):
                    self.logger.warning(f"Title contains timestamp-like pattern: {title}")
                
                # Use timestamp consistently 
                doc_id = f"doc_{formatted_timestamp}_{self._slugify(title)}"
                
                doc = {
                    "id": doc_id,
                    "type": "reference",
                    "title": title,
                    "content": content,
                    "tags": tags or [],
                    "created_at": timestamp.isoformat(),
                    "metadata": {
                        "source": source or "user_input",
                        "format": "text"
                    }
                }
                
                result = self.es_client.index(
                    index="context_store",
                    body=doc,
                    id=doc_id
                )
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                self.logger.error(f"Error storing reference: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]        

        @mcp.tool(description="Store code artifacts like code examples or templates")
        async def store_artifact(title: str, content: str, language: str = "text", 
                                tags: List[str] = None) -> list[TextContent]:
            """
            Store code artifacts like examples or templates.
            
            Args:
                title: Title of the artifact
                content: The code content
                language: Programming language of the content
                tags: Tags for categorizing and searching
            """
            self.logger.info(f"Storing artifact: {title}")
            try:
                doc_id = f"art_{datetime.now().strftime('%Y%m%dT%H-%M')}_{self._slugify(title)}"
                
                doc = {
                    "id": doc_id,
                    "type": "artifact",
                    "title": title,
                    "content": content,
                    "tags": tags or [],
                    "created_at": datetime.now().isoformat(),
                    "metadata": {
                        "language": language,
                        "format": "code"
                    }
                }
                
                result = self.es_client.index(
                    index="context_store",
                    body=doc,
                    id=doc_id
                )
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                self.logger.error(f"Error storing artifact: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @mcp.tool(description="Search across all context types or filter by type")
        async def search_context(query: str, types: List[str] = None, 
                               tags: List[str] = None, limit: int = 10) -> list[TextContent]:
            """
            Search across all context types.
            
            Args:
                query: Search query
                types: Types to filter by (session, log, reference, artifact)
                tags: Filter results by tags
                limit: Maximum number of results
            """
            self.logger.info(f"Searching context: {query}")
            try:
                # Build query
                query_body = {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "content", "key_points", "next_steps"],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                }
                
                # Add filters
                filters = []
                
                if types:
                    filters.append({"terms": {"type": types}})
                
                if tags:
                    filters.append({"terms": {"tags": tags}})
                
                if filters:
                    query_body["bool"]["filter"] = filters
                
                # Execute search
                result = self.es_client.search(
                    index="context_store",
                    body={
                        "query": query_body,
                        "size": limit,
                        "sort": [
                            {"_score": {"order": "desc"}},
                            {"created_at": {"order": "desc"}}
                        ]
                    }
                )
                
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                self.logger.error(f"Error searching context: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        @mcp.tool(description="List recent context by type, generally we are looking for whatever was most recently logged to get back up to speed. AI or Human usage encouraged.")
        async def list_recent(type: str = None, limit: int = 1) -> list[TextContent]:
            """
            List recent context entries, optionally filtered by type.
            
            Args:
                type: Type to filter by (session, log, reference, artifact)
                limit: Maximum number of results
            """
            try:
                # Build query
                query = {"match_all": {}}
                
                # Add type filter if specified
                if type:
                    query = {
                        "bool": {
                            "must": [{"match_all": {}}],
                            "filter": [{"term": {"type": type}}]
                        }
                    }
                
                # Execute search
                result = self.es_client.search(
                    index="context_store",
                    body={
                        "query": query,
                        "size": limit,
                        "sort": [{"created_at": {"order": "desc"}}]
                    }
                )
                
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                self.logger.error(f"Error listing recent context: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _slugify(self, text: str) -> str:
        """Create a URL-friendly version of a string."""
        import re
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        text = re.sub(r'-+', '-', text)
        return text.strip('-')[:50]
