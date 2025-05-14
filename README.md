# OpenSearch MCP Server

## Overview

A Model Context Protocol (MCP) server implementation that provides OpenSearch interaction capabilities. This server enables searching documents, managing indices, and monitoring cluster health through a set of tools designed to be used by AI assistants like Claude.

This is a fork of [elastic-mcp-server](https://github.com/cr7258/elasticsearch-mcp-server) that has been converted to work with OpenSearch instead of Elasticsearch.

## Features

### Index Operations

- `list_indices`: List all indices in the OpenSearch cluster
- `get_mapping`: Retrieve the mapping configuration for a specific index
- `get_settings`: Get the settings configuration for a specific index
- `create_index`: Create a new index with specified settings and mappings
- `delete_index`: Delete an index from the cluster
- `configure_indices`: Automatically create indices based on YAML configuration files

### Document Operations

- `search_documents`: Search documents in an index using OpenSearch Query DSL
- `index_document`: Index a document into an index
- `delete_document`: Delete a document from an index
- `update_by_query`: Update documents matching a query
- `get_document`: Get a document by ID

### Cluster Operations

- `get_cluster_health`: Get health status of the cluster
- `get_cluster_stats`: Get statistical information about the cluster

## Configuration-Driven Architecture

The server uses a configuration-driven approach for index management, reading YAML files from the `configs/indices` directory to define index structures. This makes the system more maintainable and adaptable to changing requirements.

### YAML Configuration Structure

Index configurations follow this pattern:

```yaml
index_name: my_index
settings:
  number_of_shards: 1
  number_of_replicas: 0
mappings:
  properties:
    id:
      type: keyword
    title:
      type: text
    # Additional field definitions here
```

To add a new index, simply create a new YAML file in the `configs/indices` directory and run the `configure_indices` tool.

## Starting OpenSearch Cluster

Start the OpenSearch cluster using Docker Compose:

```bash
docker-compose up -d
```

This will start a 3-node OpenSearch cluster and Kibana. Default OpenSearch username is `opensearch` with password `test123`.

You can access Kibana from http://localhost:5601.

## Usage with Claude Desktop

### Using uv with local development

Using `uv` requires cloning the repository locally and specifying the path to the source code. Add the following configuration to Claude Desktop's config file `claude_desktop_config.json`.

You need to change `path/to/src/opensearch_mcp_server` to the path where you cloned the repository.

```json
{
  "mcpServers": {
    "opensearch": {
      "command": "uv",
      "args": [
        "--directory",
        "path/to/src/opensearch_mcp_server",
        "run",
        "opensearch-mcp-server"
      ],
      "env": {
        "OPENSEARCH_HOST": "https://localhost:9200",
        "OPENSEARCH_USERNAME": "opensearch",
        "OPENSEARCH_PASSWORD": "test123"
      }
    }
  }
}
```

- On macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

Restart Claude Desktop to load the new MCP server.

## Interacting with OpenSearch through Claude

Now you can interact with your OpenSearch cluster through Claude using natural language commands like:

- "List all indices in the cluster"
- "Create a new index named products with title and price fields"
- "Search for documents about AI in the context_store index"
- "Show me the cluster health status"
- "Configure all indices using the YAML files"

## License

This project is licensed under the Apache License Version 2.0 - see the [LICENSE](LICENSE) file for details.
