#!/usr/bin/env python3
import logging
import os
from fastmcp import FastMCP
from .tools.index import IndexTools
from .tools.document import DocumentTools
from .tools.cluster import ClusterTools
from .tools.memory import MemoryTools

class OpensearchMCPServer:
    def __init__(self):
        self.name = "opensearch_mcp_server"
        self.mcp = FastMCP(self.name)
        
        # Configure logging
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.name)
        
        # Log startup information
        self.logger.info(f"Starting {self.name} with log level {log_level}")
        self.logger.info(f"Python environment: {os.environ.get('PYTHONPATH', 'Not set')}")
        
        # Initialize tools
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools."""
        # Initialize tool classes
        index_tools = IndexTools(self.logger)
        document_tools = DocumentTools(self.logger)
        cluster_tools = ClusterTools(self.logger)
        memory_tools = MemoryTools(self.logger)
        
        # Register tools from each module
        self.logger.info("Registering index tools...")
        index_tools.register_tools(self.mcp)
        
        self.logger.info("Registering document tools...")
        document_tools.register_tools(self.mcp)
        
        self.logger.info("Registering cluster tools...")
        cluster_tools.register_tools(self.mcp)
        
        self.logger.info("Registering memory tools...")
        memory_tools.register_tools(self.mcp)
        
        self.logger.info("All tools registered successfully")

    def run(self):
        """Run the MCP server."""
        self.logger.info(f"Starting {self.name} MCP server")
        self.mcp.run()

def main():
    try:
        server = OpensearchMCPServer()
        server.run()
    except Exception as e:
        logging.error(f"Fatal error starting server: {str(e)}", exc_info=True)
        raise
