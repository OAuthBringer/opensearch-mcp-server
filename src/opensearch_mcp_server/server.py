#!/usr/bin/env python3
import logging
from fastmcp import FastMCP
from .tools.index import IndexTools
from .tools.document import DocumentTools
from .tools.cluster import ClusterTools

class OpensearchMCPServer:
    def __init__(self):
        self.name = "opensearch_mcp_server"
        self.mcp = FastMCP(self.name)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.name)
        self.tools = [
            IndexTools, 
            DocumentTools, 
            ClusterTools
        ]
        
        # Initialize tools
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools."""

        for tool in self.tools:
            tool(self.logger).register_tools(self.mcp)

    def run(self):
        """Run the MCP server."""
        self.mcp.run()

def main():
    server = OpensearchMCPServer()
    server.run()
