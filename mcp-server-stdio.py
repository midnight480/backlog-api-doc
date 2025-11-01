#!/usr/bin/env python3
"""
MCP Server stdio wrapper for HTTP-based server
This allows MCP clients to communicate via stdio while the actual server runs as HTTP.
"""
import sys
import json
import httpx
from typing import Any, Dict

MCP_SERVER_URL = "http://localhost:58080"

# MCP method to HTTP endpoint mapping
METHOD_MAP = {
    "tools/call": {
        "search_backlog_api": "/mcp/search_backlog_api",
        "get_api_spec": "/mcp/get_api_spec",
        "list_api_categories": "/mcp/list_api_categories",
        "get_error_info": "/mcp/get_error_info",
    },
    "initialize": "/health",
    "tools/list": None,  # Returns static tool list
}

# Tool definitions
TOOLS = [
    {
        "name": "search_backlog_api",
        "description": "Search Backlog API documentation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (endpoint name, function name, etc.)"
                },
                "category": {
                    "type": "string",
                    "description": "Category filter (optional)",
                    "enum": ["authentication", "endpoints", "errors", "sdks"]
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_api_spec",
        "description": "Get detailed specification of a specific API",
        "inputSchema": {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "API endpoint (e.g., GET /api/v2/issues)"
                }
            },
            "required": ["endpoint"]
        }
    },
    {
        "name": "list_api_categories",
        "description": "Get list of API categories",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_error_info",
        "description": "Get error code information",
        "inputSchema": {
            "type": "object",
            "properties": {
                "error_code": {
                    "type": "string",
                    "description": "Error code (e.g., 40001)"
                }
            },
            "required": ["error_code"]
        }
    }
]


def send_response(response: Dict[str, Any]):
    """Send JSON-RPC response"""
    try:
        json.dump(response, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
    except (BrokenPipeError, IOError):
        # Client disconnected, exit gracefully
        sys.exit(0)


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP JSON-RPC request"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    try:
        if method == "initialize":
            # Return server capabilities
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "backlog-api-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": TOOLS
                }
            }
        
        elif method.startswith("notifications/"):
            # Notifications don't require a response
            return None
        
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})
            
            # Map to HTTP endpoint
            endpoint_map = METHOD_MAP["tools/call"]
            if tool_name not in endpoint_map:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            endpoint = endpoint_map[tool_name]
            
            # Make HTTP request
            client = httpx.Client(timeout=30.0)
            try:
                if tool_name == "list_api_categories":
                    response = client.get(f"{MCP_SERVER_URL}{endpoint}")
                else:
                    response = client.post(f"{MCP_SERVER_URL}{endpoint}", json=tool_params)
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
            finally:
                client.close()
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }


def main():
    """Main stdio loop"""
    # Ensure unbuffered output for real-time communication
    sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None
    
    # Process requests from stdin
    # Note: Health check is done lazily in handle_request to allow initialization
    try:
        for line in sys.stdin:
            if not line or not line.strip():
                continue
            try:
                request = json.loads(line.strip())
                method = request.get("method")
                
                # Handle initialize request immediately without health check
                if method == "initialize":
                    response = handle_request(request)
                    send_response(response)
                    continue
                
                # Handle notifications (no response needed)
                if method and method.startswith("notifications/"):
                    # This is a notification, silently ignore (no response needed)
                    continue
                
                # For other requests, verify HTTP server is available
                try:
                    client = httpx.Client(timeout=5.0)
                    health_response = client.get(f"{MCP_SERVER_URL}/health", timeout=2.0)
                    client.close()
                    if health_response.status_code != 200:
                        send_response({
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "error": {
                                "code": -32000,
                                "message": f"HTTP server not available: {health_response.status_code}"
                            }
                        })
                        continue
                except Exception as e:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32000,
                            "message": f"HTTP server not available: {str(e)}. Make sure Docker container 'backlog-api-mcp' is running."
                        }
                    })
                    continue
                
                response = handle_request(request)
                # Skip sending response for notifications (they don't have id)
                if response is not None:
                    send_response(response)
            except json.JSONDecodeError as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                })
            except Exception as e:
                send_response({
                    "jsonrpc": "2.0",
                    "id": request.get("id") if 'request' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                })
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:
        # Client disconnected, exit gracefully
        pass
    except Exception as e:
        # Unexpected error, try to send error response
        try:
            send_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Unexpected error: {str(e)}"
                }
            })
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
