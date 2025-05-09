"""
Configuration Utilities for Slarglebart Memory System

This module provides configuration management for the OpenSearch MCP Server
with vector search capabilities.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    # Embedding configuration
    "embedding_model": "intfloat/e5-small-v2",
    "embedding_dimension": 384,
    "normalize_embeddings": True,
    
    # OpenSearch configuration
    "index_settings": {
        "index.knn": True,
        "index.knn.space_type": "l2"
    },
    
    # Memory configuration
    "default_memory_index": "slarglebart_memories_v2",
    "legacy_memory_index": "slarglebart_memories",
    "confidence_decay_rate": 0.05,  # 5% per week
    
    # Search configuration
    "vector_search_weight": 0.7,  # Weight of vector similarity in hybrid search
    "keyword_search_weight": 0.3,  # Weight of keyword matching in hybrid search
    "default_search_size": 10,  # Default number of results to return
    "minimum_score": 0.3  # Minimum score to include in results
}


def get_config(key: Optional[str] = None) -> Any:
    """
    Get configuration value, checking environment variables first,
    then falling back to default values.
    
    Args:
        key: Optional key to get specific config value, returns full config if None
        
    Returns:
        Configuration value or dictionary
    """
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Environment variable overrides
    env_mappings = {
        "embedding_model": "EMBEDDING_MODEL",
        "embedding_dimension": "EMBEDDING_DIMENSION",
        "default_memory_index": "MEMORY_INDEX",
        "vector_search_weight": "VECTOR_SEARCH_WEIGHT",
        "keyword_search_weight": "KEYWORD_SEARCH_WEIGHT"
    }
    
    # Update config with environment variables
    for config_key, env_var in env_mappings.items():
        if env_var in os.environ:
            env_value = os.environ[env_var]
            
            # Convert types appropriately
            if isinstance(config[config_key], bool):
                config[config_key] = env_value.lower() in ('true', 'yes', '1')
            elif isinstance(config[config_key], int):
                try:
                    config[config_key] = int(env_value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {env_var}: {env_value}")
            elif isinstance(config[config_key], float):
                try:
                    config[config_key] = float(env_value)
                except ValueError:
                    logger.warning(f"Invalid float value for {env_var}: {env_value}")
            else:
                config[config_key] = env_value
    
    # Return specific key or full config
    if key is not None:
        return config.get(key, None)
    
    return config


def get_index_mapping() -> Dict[str, Any]:
    """
    Get the default mapping for the memory index with vector search support.
    
    Returns:
        Dictionary containing the mapping definition
    """
    # Get embedding dimension from config
    dimension = get_config("embedding_dimension")
    
    return {
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
                "dimension": dimension,
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


def get_index_settings() -> Dict[str, Any]:
    """
    Get the default settings for the memory index with vector search support.
    
    Returns:
        Dictionary containing the index settings
    """
    return {
        "settings": {
            "index": get_config("index_settings")
        }
    }


def get_hybrid_search_query(
    text_query: str,
    embedding: list,
    size: int = None,
    memory_type: Optional[str] = None,
    time_range: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Generate a hybrid search query combining vector similarity and text matching.
    
    Args:
        text_query: Text query for keyword matching
        embedding: Vector embedding for similarity search
        size: Number of results to return, defaults to config value
        memory_type: Optional filter by memory type
        time_range: Optional time range filter with 'gte' and 'lte' keys
        
    Returns:
        Dictionary containing the OpenSearch query
    """
    # Get search weights from config
    vector_weight = get_config("vector_search_weight")
    keyword_weight = get_config("keyword_search_weight")
    result_size = size or get_config("default_search_size")
    
    # Build query filters
    filters = []
    
    if memory_type:
        filters.append({"term": {"memory_type": memory_type}})
    
    if time_range and isinstance(time_range, dict):
        time_filter = {"range": {"created_at": {}}}
        
        if "gte" in time_range:
            time_filter["range"]["created_at"]["gte"] = time_range["gte"]
        
        if "lte" in time_range:
            time_filter["range"]["created_at"]["lte"] = time_range["lte"]
        
        if time_filter["range"]["created_at"]:
            filters.append(time_filter)
    
    # Base query structure
    query = {
        "size": result_size,
        "query": {
            "bool": {
                "should": [
                    # Vector similarity component
                    {
                        "knn": {
                            "embedding": {
                                "vector": embedding,
                                "k": result_size * 2  # Get more candidates for scoring
                            }
                        }
                    },
                    # Text matching component
                    {
                        "multi_match": {
                            "query": text_query,
                            "fields": ["title^2", "content", "key_points", "tags^1.5"],
                            "type": "best_fields"
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        },
        # Custom scoring to combine vector and keyword relevance
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": f"({vector_weight} * cosineSimilarity(params.query_vector, 'embedding')) + ({keyword_weight} * _score)",
                "params": {
                    "query_vector": embedding
                }
            }
        }
    }
    
    # Add filters if present
    if filters:
        query["query"]["bool"]["filter"] = filters
    
    return query
