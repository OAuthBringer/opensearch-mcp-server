"""
Memory Tools for Slarglebart Memory System

This module provides tools for working with the Slarglebart memory system,
including vector-based semantic search, memory creation, and retrieval.
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..es_client import OpensearchClient
from ..utils.embeddings import generate_embedding, prepare_text_for_embedding, enrich_document_with_embedding
from ..utils.config import get_config, get_hybrid_search_query
from mcp.types import TextContent


class MemoryTools(OpensearchClient):
    def register_tools(self, mcp: Any):
        """Register memory-related tools."""
        
        @mcp.tool(description="Store a memory with automatic embedding generation")
        async def store_memory(
            memory_type: str,
            title: str,
            content: str,
            memory_id: Optional[str] = None,
            tags: Optional[List[str]] = None,
            metadata: Optional[Dict[str, Any]] = None
        ) -> list[TextContent]:
            """
            Store a memory in the memory system with automatic embedding generation.
            
            Args:
                memory_type: Type of memory (episodic, semantic, procedural, associative)
                title: Title or summary of the memory
                content: Content of the memory
                memory_id: Optional unique ID (will be generated if not provided)
                tags: Optional list of tags for categorization
                metadata: Optional metadata dictionary
            """
            self.logger.info(f"Storing memory of type: {memory_type} with title: {title}")
            
            try:
                # Get default memory index from config
                memory_index = get_config("default_memory_index")
                
                # Generate a memory_id if not provided
                if not memory_id:
                    memory_id = f"memory_{uuid.uuid4().hex[:8]}"
                
                # Current timestamp
                timestamp = datetime.utcnow().isoformat()
                
                # Create the document
                document = {
                    "memory_id": memory_id,
                    "memory_type": memory_type,
                    "title": title,
                    "content": content,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "tags": tags or [],
                    "confidence": 1.0,
                    "access_count": 1,
                    "last_accessed": timestamp,
                    "metadata": metadata or {
                        "confidence": 1.0,
                        "access_count": 1,
                        "source": "direct_creation"
                    }
                }
                
                # Enrich document with embedding
                enriched_document = enrich_document_with_embedding(document)
                
                # Index the document
                response = self.es_client.index(
                    index=memory_index,
                    id=memory_id,
                    body=enriched_document,
                    refresh=True  # Make immediately available for search
                )
                
                return [TextContent(type="text", text=f"Memory stored successfully with ID: {memory_id}")]
            except Exception as e:
                self.logger.error(f"Error storing memory: {e}")
                return [TextContent(type="text", text=f"Error storing memory: {str(e)}")]

        @mcp.tool(description="Store an episodic (session) memory with key points and next steps")
        async def store_session_memory(
            session_id: str,
            title: str,
            summary: str,
            key_points: List[str],
            next_steps: List[str],
            memory_id: Optional[str] = None,
            tags: Optional[List[str]] = None,
            metadata: Optional[Dict[str, Any]] = None
        ) -> list[TextContent]:
            """
            Store an episodic memory representing a session with key points and next steps.
            
            Args:
                session_id: Unique session identifier
                title: Title of the session
                summary: Summary of the session
                key_points: List of key points from the session
                next_steps: List of next steps identified
                memory_id: Optional unique ID (will be generated if not provided)
                tags: Optional list of tags for categorization
                metadata: Optional metadata dictionary
            """
            self.logger.info(f"Storing session memory with ID: {session_id} and title: {title}")
            
            try:
                # Get default memory index from config
                memory_index = get_config("default_memory_index")
                
                # Generate a memory_id if not provided
                if not memory_id:
                    memory_id = f"session_{uuid.uuid4().hex[:8]}"
                
                # Current timestamp
                timestamp = datetime.utcnow().isoformat()
                
                # Create the document
                document = {
                    "memory_id": memory_id,
                    "memory_type": "episodic",
                    "title": title,
                    "content": summary,  # Main content is the summary
                    "session_id": session_id,
                    "key_points": key_points,
                    "next_steps": next_steps,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "tags": tags or [],
                    "confidence": 1.0,
                    "access_count": 1,
                    "last_accessed": timestamp,
                    "metadata": metadata or {
                        "confidence": 1.0,
                        "access_count": 1,
                        "source": "session_summary"
                    }
                }
                
                # Prepare text for embedding - combine all relevant fields
                text_for_embedding = f"{title} {summary} " + " ".join(key_points)
                
                # Generate embedding
                document["embedding"] = generate_embedding(text_for_embedding)
                
                # Index the document
                response = self.es_client.index(
                    index=memory_index,
                    id=memory_id,
                    body=document,
                    refresh=True  # Make immediately available for search
                )
                
                return [TextContent(type="text", text=f"Session memory stored successfully with ID: {memory_id}")]
            except Exception as e:
                self.logger.error(f"Error storing session memory: {e}")
                return [TextContent(type="text", text=f"Error storing session memory: {str(e)}")]

        @mcp.tool(description="Create a connection between two memories")
        async def create_memory_connection(
            source_id: str,
            target_id: str,
            relationship_type: str,
            description: str,
            strength: float = 0.5,
            memory_id: Optional[str] = None,
            tags: Optional[List[str]] = None
        ) -> list[TextContent]:
            """
            Create a connection between two existing memories.
            
            Args:
                source_id: ID of the source memory
                target_id: ID of the target memory
                relationship_type: Type of relationship (e.g., "part_of", "causes", "implements")
                description: Description of the connection
                strength: Connection strength from 0.0 to 1.0
                memory_id: Optional unique ID (will be generated if not provided)
                tags: Optional list of tags for the connection
            """
            self.logger.info(f"Creating connection from {source_id} to {target_id} of type {relationship_type}")
            
            try:
                # Get default memory index from config
                memory_index = get_config("default_memory_index")
                
                # Generate a memory_id if not provided
                if not memory_id:
                    memory_id = f"connection_{uuid.uuid4().hex[:8]}"
                
                # Current timestamp
                timestamp = datetime.utcnow().isoformat()
                
                # Verify source and target memories exist
                source_exists = self.es_client.exists(index=memory_index, id=source_id)
                target_exists = self.es_client.exists(index=memory_index, id=target_id)
                
                if not source_exists or not target_exists:
                    missing = []
                    if not source_exists:
                        missing.append(f"Source memory {source_id}")
                    if not target_exists:
                        missing.append(f"Target memory {target_id}")
                    
                    return [TextContent(type="text", text=f"Cannot create connection - {', '.join(missing)} not found")]
                
                # Create the document
                document = {
                    "memory_id": memory_id,
                    "memory_type": "associative",
                    "title": f"Connection: {relationship_type}",
                    "content": description,
                    "source_id": source_id,
                    "target_id": target_id,
                    "relationship_type": relationship_type,
                    "strength": strength,
                    "created_at": timestamp,
                    "updated_at": timestamp,
                    "tags": tags or [],
                    "confidence": 1.0,
                    "access_count": 1,
                    "last_accessed": timestamp,
                    "metadata": {
                        "confidence": 1.0,
                        "access_count": 1,
                        "source": "explicit_connection"
                    }
                }
                
                # Prepare text for embedding
                text_for_embedding = f"{relationship_type} {description} connection from {source_id} to {target_id}"
                
                # Generate embedding
                document["embedding"] = generate_embedding(text_for_embedding)
                
                # Index the document
                response = self.es_client.index(
                    index=memory_index,
                    id=memory_id,
                    body=document,
                    refresh=True
                )
                
                return [TextContent(type="text", text=f"Connection created successfully with ID: {memory_id}")]
            except Exception as e:
                self.logger.error(f"Error creating memory connection: {e}")
                return [TextContent(type="text", text=f"Error creating memory connection: {str(e)}")]

        @mcp.tool(description="Search memories using semantic search")
        async def semantic_search_memories(
            query: str,
            memory_type: Optional[str] = None,
            size: int = 10,
            min_score: float = 0.3
        ) -> list[TextContent]:
            """
            Search memories using hybrid semantic and keyword search.
            
            Args:
                query: Search query text
                memory_type: Optional filter by memory type
                size: Number of results to return
                min_score: Minimum score threshold for results
            """
            self.logger.info(f"Semantic searching memories with query: {query}")
            
            try:
                # Get default memory index from config
                memory_index = get_config("default_memory_index")
                
                # Generate embedding for the query
                embedding = generate_embedding(query)
                
                # Create the hybrid search query
                search_query = get_hybrid_search_query(
                    text_query=query,
                    embedding=embedding,
                    size=size,
                    memory_type=memory_type
                )
                
                # Execute search
                response = self.es_client.search(
                    index=memory_index,
                    body=search_query
                )
                
                # Process results
                hits = response.get("hits", {}).get("hits", [])
                
                if not hits:
                    return [TextContent(type="text", text="No memories found matching the query.")]
                
                # Format results
                results = []
                for i, hit in enumerate(hits):
                    score = hit.get("_score", 0)
                    if score < min_score:
                        continue
                        
                    source = hit.get("_source", {})
                    
                    # Format based on memory type
                    memory_type = source.get("memory_type", "unknown")
                    
                    if memory_type == "episodic":
                        result = (
                            f"Memory {i+1}: {source.get('title', 'Untitled')} (Score: {score:.2f})\n"
                            f"Type: {memory_type}\n"
                            f"Content: {source.get('content', 'No content')}\n"
                            f"Key Points: {', '.join(source.get('key_points', []))}\n"
                            f"Created: {source.get('created_at', 'Unknown')}\n"
                            f"Tags: {', '.join(source.get('tags', []))}\n"
                            f"ID: {source.get('memory_id', hit.get('_id', 'Unknown'))}\n"
                        )
                    elif memory_type == "associative":
                        result = (
                            f"Connection {i+1}: {source.get('title', 'Untitled')} (Score: {score:.2f})\n"
                            f"Type: {memory_type}\n"
                            f"Relationship: {source.get('relationship_type', 'related')}\n"
                            f"Description: {source.get('content', 'No description')}\n"
                            f"From: {source.get('source_id', 'Unknown')} To: {source.get('target_id', 'Unknown')}\n"
                            f"Strength: {source.get('strength', 0.5)}\n"
                            f"Created: {source.get('created_at', 'Unknown')}\n"
                            f"ID: {source.get('memory_id', hit.get('_id', 'Unknown'))}\n"
                        )
                    else:
                        result = (
                            f"Memory {i+1}: {source.get('title', 'Untitled')} (Score: {score:.2f})\n"
                            f"Type: {memory_type}\n"
                            f"Content: {source.get('content', 'No content')}\n"
                            f"Created: {source.get('created_at', 'Unknown')}\n"
                            f"Tags: {', '.join(source.get('tags', []))}\n"
                            f"ID: {source.get('memory_id', hit.get('_id', 'Unknown'))}\n"
                        )
                    
                    results.append(result)
                
                # Update access count for retrieved memories
                memory_ids = [hit.get("_id") for hit in hits[:5]]  # Update top 5 results
                self._update_access_stats(memory_index, memory_ids)
                
                return [TextContent(type="text", text="\n\n".join(results))]
            except Exception as e:
                self.logger.error(f"Error searching memories: {e}")
                return [TextContent(type="text", text=f"Error searching memories: {str(e)}")]

        @mcp.tool(description="Get last session memory")
        async def get_last_session_memory() -> list[TextContent]:
            """
            Retrieve the most recent session memory.
            """
            self.logger.info("Retrieving last session memory")
            
            try:
                # Get default memory index from config
                memory_index = get_config("default_memory_index")
                
                # Create the search query for the most recent episodic memory
                query = {
                    "size": 1,
                    "query": {
                        "term": {
                            "memory_type": "episodic"
                        }
                    },
                    "sort": [
                        {"created_at": {"order": "desc"}}
                    ]
                }
                
                # Execute search
                response = self.es_client.search(
                    index=memory_index,
                    body=query
                )
                
                # Process results
                hits = response.get("hits", {}).get("hits", [])
                
                if not hits:
                    # Try the legacy index if no results
                    legacy_index = get_config("legacy_memory_index")
                    response = self.es_client.search(
                        index=legacy_index,
                        body=query
                    )
                    hits = response.get("hits", {}).get("hits", [])
                    
                    if not hits:
                        return [TextContent(type="text", text="No session memories found.")]
                
                # Get the most recent session
                session = hits[0].get("_source", {})
                
                # Format result based on structure
                if "content" in session and isinstance(session["content"], dict) and "summary" in session["content"]:
                    # Legacy format with nested content
                    content = session["content"]
                    result = (
                        f"Session: {session.get('title', 'Untitled Session')}\n"
                        f"Date: {session.get('created_at', 'Unknown')}\n\n"
                        f"Summary: {content.get('summary', 'No summary available')}\n\n"
                        f"Key Points:\n" + "\n".join([f"- {point}" for point in content.get('key_points', [])]) + "\n\n"
                        f"Next Steps:\n" + "\n".join([f"- {step}" for step in content.get('next_steps', [])])
                    )
                else:
                    # New flat format
                    result = (
                        f"Session: {session.get('title', 'Untitled Session')}\n"
                        f"Date: {session.get('created_at', 'Unknown')}\n\n"
                        f"Summary: {session.get('content', 'No summary available')}\n\n"
                        f"Key Points:\n" + "\n".join([f"- {point}" for point in session.get('key_points', [])]) + "\n\n"
                        f"Next Steps:\n" + "\n".join([f"- {step}" for step in session.get('next_steps', [])])
                    )
                
                # Update access stats for the retrieved memory
                self._update_access_stats(memory_index, [hits[0].get("_id")])
                
                return [TextContent(type="text", text=result)]
            except Exception as e:
                self.logger.error(f"Error retrieving last session memory: {e}")
                return [TextContent(type="text", text=f"Error retrieving last session memory: {str(e)}")]

        def _update_access_stats(self, index: str, memory_ids: List[str]) -> None:
            """
            Update access statistics for retrieved memories.
            
            Args:
                index: Index name
                memory_ids: List of memory IDs to update
            """
            if not memory_ids:
                return
                
            timestamp = datetime.utcnow().isoformat()
            
            try:
                # Use bulk API for efficiency
                actions = []
                
                for memory_id in memory_ids:
                    # Update script to increment access_count and update last_accessed
                    script = {
                        "script": {
                            "source": """
                                ctx._source.access_count = ctx._source.access_count != null ? ctx._source.access_count + 1 : 1;
                                ctx._source.last_accessed = params.timestamp;
                                if (ctx._source.metadata == null) {
                                    ctx._source.metadata = new HashMap();
                                }
                                ctx._source.metadata.access_count = ctx._source.metadata.access_count != null ? ctx._source.metadata.access_count + 1 : 1;
                            """,
                            "lang": "painless",
                            "params": {
                                "timestamp": timestamp
                            }
                        }
                    }
                    
                    actions.append({"update": {"_index": index, "_id": memory_id}})
                    actions.append(script)
                
                if actions:
                    self.es_client.bulk(body=actions)
            except Exception as e:
                self.logger.warning(f"Failed to update access stats: {e}")

        @mcp.tool(description="Initialize the memory system")
        async def initialize_memory_system() -> list[TextContent]:
            """
            Initialize or check the memory system, creating required indices if they don't exist.
            """
            self.logger.info("Initializing memory system")
            
            try:
                # Get memory index name from config
                memory_index = get_config("default_memory_index")
                
                # Check if index exists
                index_exists = self.es_client.indices.exists(index=memory_index)
                
                if not index_exists:
                    # Create the index with proper mapping for vector search
                    index_settings = {
                        "settings": {
                            "index": {
                                "knn": True,
                                "knn.space_type": "l2"
                            }
                        },
                        "mappings": {
                            "properties": {
                                # Core fields
                                "memory_id": {"type": "keyword"},
                                "memory_type": {"type": "keyword"},
                                "title": {"type": "text"},
                                "content": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                                "created_at": {"type": "date"},
                                "updated_at": {"type": "date"},
                                "tags": {"type": "keyword"},
                                
                                # Vector embedding field
                                "embedding": {
                                    "type": "knn_vector",
                                    "dimension": get_config("embedding_dimension"),
                                    "method": {
                                        "engine": "faiss",
                                        "space_type": "l2",
                                        "name": "hnsw",
                                        "parameters": {}
                                    }
                                },
                                
                                # Additional fields
                                "confidence": {"type": "float"},
                                "access_count": {"type": "integer"},
                                "last_accessed": {"type": "date"},
                                
                                # Fields for episodic memories
                                "session_id": {"type": "keyword"},
                                "key_points": {"type": "text"},
                                "next_steps": {"type": "text"},
                                
                                # Fields for associative memories
                                "source_id": {"type": "keyword"},
                                "target_id": {"type": "keyword"},
                                "relationship_type": {"type": "keyword"},
                                "strength": {"type": "float"},
                                
                                # Enhanced metadata
                                "metadata": {
                                    "properties": {
                                        "confidence": {"type": "float"},
                                        "access_count": {"type": "long"},
                                        "source": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}}
                                    }
                                }
                            }
                        }
                    }
                    
                    # Create the index
                    response = self.es_client.indices.create(index=memory_index, body=index_settings)
                    return [TextContent(type="text", text=f"Memory system initialized with new index: {memory_index}")]
                else:
                    # Check if index has proper mapping for vector search
                    mapping = self.es_client.indices.get_mapping(index=memory_index)
                    
                    # Check if embedding field exists
                    has_embedding = False
                    if memory_index in mapping:
                        properties = mapping[memory_index].get("mappings", {}).get("properties", {})
                        has_embedding = "embedding" in properties and properties["embedding"].get("type") == "knn_vector"
                    
                    if has_embedding:
                        return [TextContent(type="text", text=f"Memory system already initialized with proper vector capabilities. Index: {memory_index}")]
                    else:
                        return [TextContent(type="text", text=f"Memory index {memory_index} exists but does not have vector search capabilities. Consider reindexing.")]
            except Exception as e:
                self.logger.error(f"Error initializing memory system: {e}")
                return [TextContent(type="text", text=f"Error initializing memory system: {str(e)}")]

        @mcp.tool(description="Create a backup of the memory system")
        async def backup_memory_system() -> list[TextContent]:
            """
            Create a backup of the memory system using OpenSearch snapshot capability.
            """
            self.logger.info("Backing up memory system")
            
            try:
                # Get memory index from config
                memory_index = get_config("default_memory_index")
                
                # Generate backup name with timestamp
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_name = f"slarglebart_backup_{timestamp}"
                
                # Check if repository exists
                repo_exists = False
                try:
                    repo_info = self.es_client.snapshot.get_repository(repository="_all")
                    repo_exists = "slarglebart_backups" in repo_info
                except:
                    repo_exists = False
                
                # Create repository if it doesn't exist
                if not repo_exists:
                    # Note: This requires path.repo setting in opensearch.yml
                    repo_settings = {
                        "type": "fs",
                        "settings": {
                            "location": "slarglebart_backups"
                        }
                    }
                    
                    try:
                        self.es_client.snapshot.create_repository(
                            repository="slarglebart_backups",
                            body=repo_settings
                        )
                    except Exception as e:
                        return [TextContent(type="text", text=f"Failed to create backup repository. Make sure path.repo is configured in OpenSearch settings. Error: {str(e)}")]
                
                # Create the snapshot
                snapshot_settings = {
                    "indices": memory_index,
                    "ignore_unavailable": True,
                    "include_global_state": False
                }
                
                response = self.es_client.snapshot.create(
                    repository="slarglebart_backups",
                    snapshot=backup_name,
                    body=snapshot_settings
                )
                
                if response.get("accepted", False):
                    return [TextContent(type="text", text=f"Memory backup initiated successfully. Backup name: {backup_name}")]
                else:
                    return [TextContent(type="text", text=f"Memory backup request accepted but returned unexpected response: {response}")]
            except Exception as e:
                self.logger.error(f"Error backing up memory system: {e}")
                return [TextContent(type="text", text=f"Error backing up memory system: {str(e)}")]
