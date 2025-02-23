from typing import Annotated, Sequence, TypedDict, Dict
from langchain_core.messages import ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
import json
from src.prompts import SYSTEM_PROMPT
from src.shared import initialize_tools, bind_tools_to_chat, get_tools_by_name
from pydantic import BaseModel

__all__ = ["AgentState", "call_model", "should_continue", "tool_node"]


class AgentState(TypedDict):
    """The state of the agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]



def tool_node(state: AgentState) -> Dict[str, Sequence[ToolMessage]]:
    outputs = []
    tools_by_name = get_tools_by_name(initialize_tools())  # Convert list to dictionary
    for tool_call in state["messages"][-1].tool_calls:
        print("Available tools:", tools_by_name.keys())
        print("Requested tool:", tool_call["name"])
        # Invoke the tool and capture the result
        tool_result = tools_by_name[tool_call["name"]].invoke(tool_call["args"])
        # Convert the tool result to a dictionary if it's a Pydantic model
        if isinstance(tool_result, BaseModel):
            tool_result = tool_result.dict()
        outputs.append(
            ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": outputs}


# Define the node that calls the model
def call_model(
    state: AgentState,
    config: RunnableConfig,
) -> Dict[str, Sequence[BaseMessage]]:
    # this is similar to customizing the create_react_agent with 'prompt' parameter, but is more flexible
    system_prompt = SystemMessage(SYSTEM_PROMPT)
    
    response = bind_tools_to_chat(initialize_tools()).invoke([system_prompt] + state["messages"], config)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


# Define the conditional edge that determines whether to continue or not
def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    else:
        return "continue"