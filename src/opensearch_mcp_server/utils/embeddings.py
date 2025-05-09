"""
Embedding Utilities for Slarglebart Memory System

This module provides utilities for generating and managing vector embeddings
for semantic search capabilities in the OpenSearch MCP Server.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Union
import json

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_MODEL_NAME = "intfloat/e5-small-v2"  # 384 dimensions, good balance of quality and efficiency
DEFAULT_DIMENSION = 384
DEFAULT_NORMALIZE = True
MAX_SEQUENCE_LENGTH = 512  # Token limit for the embedding model

# Singleton pattern for model instance
_model_instance = None


def get_embedding_model(model_name: Optional[str] = None) -> SentenceTransformer:
    """
    Get or initialize the embedding model.
    Uses a singleton pattern to avoid reloading the model for each request.
    
    Args:
        model_name: Optional model name to use, defaults to environment variable or DEFAULT_MODEL_NAME
        
    Returns:
        SentenceTransformer model instance
    """
    global _model_instance
    
    if _model_instance is not None:
        return _model_instance
    
    # Get model name from env var or use default
    selected_model = model_name or os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL_NAME)
    
    try:
        logger.info(f"Loading embedding model: {selected_model}")
        _model_instance = SentenceTransformer(selected_model)
        logger.info(f"Successfully loaded embedding model with dimension: {_model_instance.get_sentence_embedding_dimension()}")
        return _model_instance
    except Exception as e:
        logger.error(f"Error loading embedding model {selected_model}: {str(e)}")
        raise


def generate_embedding(
    text: str, 
    model: Optional[SentenceTransformer] = None,
    normalize: bool = DEFAULT_NORMALIZE
) -> List[float]:
    """
    Generate embedding vector for a text string.
    
    Args:
        text: Text to generate embedding for
        model: Optional model instance, will use singleton if not provided
        normalize: Whether to normalize the embedding vector
        
    Returns:
        List of floats representing the embedding vector
    """
    if not text or not text.strip():
        logger.warning("Empty or whitespace-only text provided for embedding generation")
        # Return zero vector of appropriate dimension
        return [0.0] * DEFAULT_DIMENSION
    
    # Truncate text if too long to avoid issues with the model
    if len(text) > MAX_SEQUENCE_LENGTH * 4:  # Rough approximation of token limit
        logger.warning(f"Text too long, truncating to approximately {MAX_SEQUENCE_LENGTH} tokens")
        text = text[:MAX_SEQUENCE_LENGTH * 4]
    
    try:
        # Get or initialize model
        embedding_model = model or get_embedding_model()
        
        # Generate embedding
        embedding = embedding_model.encode(text, normalize_embeddings=normalize)
        
        # Convert to list for JSON serialization
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        # Return zero vector in case of error
        dimension = DEFAULT_DIMENSION
        if model:
            try:
                dimension = model.get_sentence_embedding_dimension()
            except:
                pass
        return [0.0] * dimension


def prepare_text_for_embedding(document: Dict[str, Any]) -> str:
    """
    Prepare a document for embedding by extracting and combining relevant text fields.
    
    Args:
        document: Document dictionary to extract text from
        
    Returns:
        Combined text string for embedding generation
    """
    text_parts = []
    
    # Always include title if present
    if "title" in document and document["title"]:
        text_parts.append(document["title"])
    
    # Extract from content field, handling different structures
    if "content" in document:
        content = document["content"]
        
        # Check if content is a dictionary
        if isinstance(content, dict):
            # Handle session/episodic format
            if "summary" in content and content["summary"]:
                text_parts.append(content["summary"])
            
            if "key_points" in content and content["key_points"]:
                if isinstance(content["key_points"], list):
                    text_parts.extend(content["key_points"])
                else:
                    text_parts.append(str(content["key_points"]))
            
            # Handle concept format
            if "description" in content and content["description"]:
                text_parts.append(content["description"])
        
        # Handle plain text content
        elif isinstance(content, str) and content:
            text_parts.append(content)
        
        # Handle potential JSON string
        elif isinstance(content, str) and content.strip().startswith('{'):
            try:
                content_obj = json.loads(content)
                if isinstance(content_obj, dict):
                    # Extract text values from the JSON
                    for key, value in content_obj.items():
                        if isinstance(value, str) and value:
                            text_parts.append(value)
            except:
                # If not valid JSON, use as is
                text_parts.append(content)
    
    # Include tags if present
    if "tags" in document and document["tags"]:
        if isinstance(document["tags"], list):
            text_parts.append(" ".join(document["tags"]))
        elif isinstance(document["tags"], str):
            text_parts.append(document["tags"])
    
    # Combine all parts
    combined_text = " ".join(text_parts)
    
    # Ensure we have some text
    if not combined_text or not combined_text.strip():
        # Use memory_id and type as fallback
        combined_text = f"{document.get('memory_id', 'unknown')} {document.get('memory_type', 'unknown')}"
    
    return combined_text.strip()


def enrich_document_with_embedding(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add embedding to a document after preparing the text.
    
    Args:
        document: Document dictionary to enrich
        
    Returns:
        Document with embedding field added
    """
    # Make a copy to avoid modifying the original
    enriched = document.copy()
    
    # Generate text for embedding
    text = prepare_text_for_embedding(document)
    
    # Generate embedding
    embedding = generate_embedding(text)
    
    # Add embedding to document
    enriched["embedding"] = embedding
    
    return enriched
