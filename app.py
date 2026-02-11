"""
FastAPI web interface for Study Tools MCP
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager, AsyncExitStack
import asyncio
import json
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

import sys
import os

from src.study_tools_mcp.config import settings
from src.study_tools_mcp.utils.logger import get_logger

logger = get_logger(__name__)

# Validate and create directories
settings.create_directories()

# Initialize OpenAI client
openai_client = None
if settings.OPENAI_API_KEY:
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# MCP session
mcp_session: Optional[ClientSession] = None
mcp_tools = []

# Conversation histories
conversations = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global mcp_session, mcp_tools

    # Startup - Connect to MCP server
    exit_stack = AsyncExitStack()
    async with exit_stack:
        try:
            settings.display()

            # Set Python path for server
            env = os.environ.copy()
            env['PYTHONPATH'] = str(settings.SRC_DIR)

            # Start MCP server
            server_params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "study_tools_mcp.server"],
                env=env
            )

            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            stdio, write = stdio_transport

            mcp_session = await exit_stack.enter_async_context(
                ClientSession(stdio, write)
            )

            await mcp_session.initialize()

            # Get available tools
            response = await mcp_session.list_tools()
            mcp_tools = convert_mcp_tools(response.tools)

            logger.info("Connected to MCP server")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")

        yield

        # Shutdown handled by exit_stack


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


def convert_mcp_tools(tools):
    """Convert MCP tools to OpenAI function format"""
    openai_tools = []
    for tool in tools:
        schema = tool.inputSchema.copy() if hasattr(tool.inputSchema, 'copy') else dict(tool.inputSchema)
        schema.pop("title", None)

        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": schema
            }
        })
    return openai_tools


async def process_with_tools(message: str, history: list) -> str:
    """Process message with OpenAI and MCP tools"""
    if not openai_client:
        return "Error: OpenAI API key not configured"

    # Add user message
    history.append({"role": "user", "content": message})

    # Call OpenAI
    response = openai_client.chat.completions.create(
        model=settings.DEFAULT_MODEL,
        messages=history,
        tools=mcp_tools,
        tool_choice="auto",
        temperature=settings.TEMPERATURE
    )

    assistant_msg = response.choices[0].message

    # Handle tool calls
    if assistant_msg.tool_calls:
        history.append({
            "role": "assistant",
            "content": assistant_msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in assistant_msg.tool_calls
            ]
        })

        # Execute tools
        for tool_call in assistant_msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            try:
                result = await mcp_session.call_tool(tool_name, tool_args)
                tool_result = "".join(
                    content.text for content in result.content if hasattr(content, 'text')
                )
            except Exception as e:
                tool_result = f"Error: {str(e)}"
                logger.error(f"Tool call error: {e}")

            history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

        # Get final response
        final_response = openai_client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=history,
            temperature=settings.TEMPERATURE
        )

        final_content = final_response.choices[0].message.content
        history.append({"role": "assistant", "content": final_content})
        return final_content
    else:
        history.append({"role": "assistant", "content": assistant_msg.content})
        return assistant_msg.content


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/files")
async def list_files():
    """List available study materials"""
    if not settings.NOTES_PATH.exists():
        return {"files": []}

    files = [
        file.name for file in settings.NOTES_PATH.iterdir()
        if file.suffix in ['.pdf', '.md']
    ]
    return {"files": sorted(files)}


@app.post("/api/chat")
async def chat(request: Request):
    """Handle chat messages with streaming"""
    data = await request.json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")

    if not message:
        return {"error": "Message is required"}

    # Get or create conversation history
    if session_id not in conversations:
        conversations[session_id] = []

    async def generate():
        try:
            response = await process_with_tools(message, conversations[session_id])

            if not response:
                yield f"data: Error: No response from server\n\n"
                yield "data: [DONE]\n\n"
                return

            # Stream response
            for line in response.split("\n"):
                yield f"data: {line}\n\n"
                await asyncio.sleep(0.02)

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Chat error: {e}")
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/chat/clear")
async def clear_conversation(request: Request):
    """Clear conversation history"""
    data = await request.json()
    session_id = data.get("session_id", "default")

    if session_id in conversations:
        conversations[session_id] = []

    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Open your browser at: http://{settings.HOST}:{settings.PORT}")

    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
