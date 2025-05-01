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
import json

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
        self.chat_history = []  # Store chat history
        self.system_prompt = """You are a helpful goal analysis and scheduling agent with a bunch of tools. 
                                  When you are using a tool, please state the tool name with a [], for example, [break_down_goal]. Also, try to format and list the details return from the tool."""

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

    async def _process_query(self, query: str) -> tuple[str, str]:
        """Process a query using Claude and available tools"""
        # Add user message to history
        self.chat_history.append({"role": "user", "content": query})
        messages = self.chat_history.copy()  # Use a copy of chat history

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-7-sonnet-20250219",
            system=self.system_prompt,
            max_tokens=5000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        final_text = []
        assistant_message_content = []
        tool_results = []

        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                # Store text content as a string instead of TextContent object
                assistant_message_content.append({"type": "text", "text": content.text})
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input
                tool_use_id = content.id

                try:
                    # Execute tool call
                    result = await self.session.call_tool(tool_name, tool_args)
                    tool_results.append({
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": result.content[0].text
                    })
                    
                    # Store tool use content as a dictionary with tool_use_id
                    assistant_message_content.append({
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_args
                    })
                    
                    # Add the assistant message with tool use to chat history
                    self.chat_history.append({
                        "role": "assistant",
                        "content": assistant_message_content
                    })
                    
                    # Add the tool result immediately after the tool use
                    # Format the tool result content correctly
                    tool_result_content = []
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            tool_result_content.append({"type": "text", "text": content_item.text})
                        else:
                            # Handle other content types if needed
                            tool_result_content.append({"type": "text", "text": str(content_item)})
                    
                    print(tool_result_content)
                    # Add tool result to chat history
                    self.chat_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": tool_result_content
                            }
                        ]
                    })

                    # Get next response from Claude using the updated chat history
                    response = self.anthropic.messages.create(
                        model="claude-3-7-sonnet-20250219",
                        system=self.system_prompt,
                        max_tokens=5000,
                        messages=self.chat_history,
                        tools=available_tools
                    )

                    if response.content:
                        final_text.append(response.content[0].text)
                        # Add Claude's final response to chat history
                        self.chat_history.append({
                            "role": "assistant",
                            "content": [{"type": "text", "text": response.content[0].text}]
                        })
                except Exception as e:
                    print(f"Error executing tool {tool_name}: {str(e)}")
                    tool_results.append({
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": f"Error: {str(e)}"
                    })
                    
                    # Add error result for the tool use to chat history
                    self.chat_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": [{"type": "text", "text": f"Error: {str(e)}"}]
                            }
                        ]
                    })

        # Return both the chat response and tool results
        return "\n".join(final_text), json.dumps(tool_results)

    def process_query(self, query: str) -> tuple[str, str]:
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
        response, tool_results = mcp_client.process_query(query)
        return jsonify({'response': response, 'tool_results': tool_results})
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