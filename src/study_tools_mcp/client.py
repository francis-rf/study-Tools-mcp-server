"""
Simple script to run the MCP client with proper server connection.
"""
import asyncio
import os
import sys
import json
from typing import Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MCPClient:
    def __init__(self):
        """Initialize the MCP client with OpenAI."""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found. Please add it to your .env file.")

        self.openai_client = OpenAI(api_key=openai_api_key)
        self.conversation_history = []

    async def connect_to_server(self):
        """Connect to the study-tools-mcp server."""
        print("Connecting to study-tools-mcp server...")

        # Use python -m to run the server as a module
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "study_tools_mcp.server"],
            env=None
        )

        # Connect to server
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport

        # Initialize session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        # Get available tools
        response = await self.session.list_tools()
        tools = response.tools

        print(f"\n✅ Connected! Available tools: {[tool.name for tool in tools]}\n")

        # Convert tools to OpenAI format
        self.tools = self._convert_tools(tools)

    def _convert_tools(self, mcp_tools):
        """Convert MCP tools to OpenAI function calling format."""
        openai_tools = []
        for tool in mcp_tools:
            # Clean the schema
            parameters = self._clean_schema(tool.inputSchema)

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters
                }
            })
        return openai_tools

    def _clean_schema(self, schema):
        """Remove 'title' fields from schema."""
        if isinstance(schema, dict):
            schema = schema.copy()
            schema.pop("title", None)

            if "properties" in schema and isinstance(schema["properties"], dict):
                schema["properties"] = {
                    key: self._clean_schema(value)
                    for key, value in schema["properties"].items()
                }

            if "items" in schema:
                schema["items"] = self._clean_schema(schema["items"])

        return schema

    async def process_query(self, query: str) -> str:
        """Process user query with OpenAI and execute tool calls."""
        # Add user message
        self.conversation_history.append({
            "role": "user",
            "content": query
        })

        # Call OpenAI
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Use a real OpenAI model
            messages=self.conversation_history,
            tools=self.tools,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message

        # Handle tool calls
        if assistant_message.tool_calls:
            # Add assistant message with tool calls
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })

            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"\n🔧 Calling tool: {tool_name}")
                print(f"   Arguments: {tool_args}")

                try:
                    result = await self.session.call_tool(tool_name, tool_args)

                    # Extract text content
                    tool_result = ""
                    for content in result.content:
                        if hasattr(content, 'text'):
                            tool_result += content.text

                    function_response = tool_result
                    print(f"✅ Tool executed successfully\n")
                except Exception as e:
                    function_response = f"Error: {str(e)}"
                    print(f"❌ Tool error: {e}\n")

                # Add tool response to history
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": function_response
                })

            # Get final response from OpenAI
            final_response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.conversation_history,
                tools=self.tools,
                tool_choice="auto"
            )

            final_message = final_response.choices[0].message
            self.conversation_history.append({
                "role": "assistant",
                "content": final_message.content
            })

            return final_message.content
        else:
            # No tool calls
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            return assistant_message.content

    async def chat_loop(self):
        """Interactive chat loop."""
        print("💬 MCP Client Started!")
        print("   Type your questions or 'quit' to exit.\n")

        while True:
            try:
                query = input("You: ").strip()
                if query.lower() in ['quit', 'exit', 'q']:
                    break

                if not query:
                    continue

                # Process query
                response = await self.process_query(query)
                print(f"\nAssistant: {response}\n")

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    """Main function."""
    client = MCPClient()
    try:
        await client.connect_to_server()
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
