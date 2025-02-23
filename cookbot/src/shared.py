from src.tools import (
    create_recipe_from_intent_tool,
    adjust_recipe_quantities_tool,
    translate_recipe_tool,
    clarify_recipe_step_tool,
    web_search_tool
)
from src.chatmodel import ChatModel

def initialize_tools():
    """Initialize and configure tools for the chat model."""
    tools = [
        create_recipe_from_intent_tool,
        adjust_recipe_quantities_tool,
        translate_recipe_tool,
        clarify_recipe_step_tool,
        web_search_tool
    ]
    tool_names = ["create_recipe_from_intent_tool", "adjust_recipe_quantities_tool", "translate_recipe_tool", "clarify_recipe_step_tool", "web_search_tool"]
    
    for tool, name in zip(tools, tool_names):
        tool.name = name
    
    return tools

def bind_tools_to_chat(tools):
    """Bind tools to the chat model."""
    return ChatModel().model.bind_tools(tools)

def get_tools_by_name(tools):
    """Create a dictionary of tools accessible by their name."""
    
    return {tool.name: tool for tool in tools}

# Initialize tools and bind them to the chat model
