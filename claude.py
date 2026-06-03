from anthropic import Anthropic
import os
import asyncio
from tools import tools
from dotenv import load_dotenv
from car import tool_get_battery_status, tool_get_lock_status, tool_lock_car, tool_unlock_car

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not set in .env file")

# Initialize Claude client
client = Anthropic(api_key=ANTHROPIC_API_KEY)

def execute_tool(tool_name):
    """Execute a tool by name and return the result as a string."""

    if tool_name == "get_battery_status":
        return tool_get_battery_status()
    elif tool_name == "get_lock_status":
        return tool_get_lock_status()
    elif tool_name == "get_location":
        return tool_get_location()
    elif tool_name == "lock_car":
        return tool_lock_car()
    elif tool_name == "unlock_car":
        return tool_unlock_car()
    else:
        return f"Unknown tool: {tool_name}"

async def handle_message_with_claude(user_message):
    """Send user message to Claude, handle tool calls, return final response."""
    messages = [{"role": "user", "content": user_message}]
    loop = asyncio.get_running_loop()
    
    while True:
        print("=== Calling Claude API ===")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )
        print(f"Stop reason: {response.stop_reason}")
        
        if response.stop_reason == "tool_use":
            print("Claude wants to call tools")
            tool_results = []
            
            for block in response.content:
                if block.type == "tool_use":
                    print(f"=== Calling tool: {block.name} ===")
                    result = await loop.run_in_executor(None, execute_tool, block.name)
                    print(f"=== Tool returned: {result} ===")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            print("=== Appending to conversation, looping back ===")
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue
        else:
            print("=== Claude finished ===")
            text_response = ""
            for block in response.content:
                if block.type == "text":
                    text_response += block.text
            print(f"=== Final response: {text_response} ===")
            return text_response if text_response else "No response from Claude"