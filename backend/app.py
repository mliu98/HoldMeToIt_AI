# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import threading

load_dotenv()

app = Flask(__name__)
CORS(app)

class MCPClientWrapper:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.is_connected = False
        self.stdio = None
        self.write = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _connect_to_server(self, server_script_path: str):
        """Connect to the MCP server (weather.py in your case)"""
        if self.is_connected:
            return

        is_python = server_script_path.endswith('.py')
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        self.is_connected = True

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    def connect_to_server(self, server_script_path: str):
        """Sync wrapper for connect_to_server"""
        future = asyncio.run_coroutine_threadsafe(self._connect_to_server(server_script_path), self.loop)
        return future.result()

    async def _process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=5000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        final_text = []
        assistant_message_content = []

        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                
                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)

    def process_query(self, query: str) -> str:
        """Sync wrapper for process_query"""
        future = asyncio.run_coroutine_threadsafe(self._process_query(query), self.loop)
        return future.result()

    async def _cleanup(self):
        """Clean up resources"""
        if self.is_connected:
            await self.exit_stack.aclose()
            self.is_connected = False

    def cleanup(self):
        """Sync wrapper for cleanup"""
        future = asyncio.run_coroutine_threadsafe(self._cleanup(), self.loop)
        future.result()

# Global client instance
mcp_client = MCPClientWrapper()

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        # Ensure connection is established
        if not mcp_client.is_connected:
            mcp_client.connect_to_server('mcp_server.py')
        
        # Process the query
        response = mcp_client.process_query(query)
        return jsonify({'response': response})
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Initialize connection at startup
def init_mcp_connection():
    try:
        mcp_client.connect_to_server('mcp_server.py')
        print("MCP connection initialized successfully")
    except Exception as e:
        print(f"Error connecting to MCP server: {str(e)}")

# Initialize the connection when the app starts
init_mcp_connection()

if __name__ == '__main__':
    app.run(debug=True, port=5000)