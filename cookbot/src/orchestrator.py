from src.langraph_utils import AgentState, call_model, should_continue, tool_node
from langgraph.graph import StateGraph, END


__all__ = ["Orchestrator"]


class Orchestrator:
    def __init__(self):
        self.workflow = StateGraph(AgentState)
        self._setup_workflow()

    def _setup_workflow(self):
        # Define the two nodes we will cycle between
        self.workflow.add_node("agent", call_model)
        self.workflow.add_node("tools", tool_node)

        # Set the entrypoint as `agent`
        self.workflow.set_entry_point("agent")

        # Add a conditional edge
        self.workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )
        # Add a normal edge from `tools` to `agent`
        self.workflow.add_edge("tools", "agent")

    def stream(self, inputs, stream_mode="values"):
        # Compile the graph and stream responses
        graph = self.workflow.compile()
        return graph.stream(inputs, stream_mode=stream_mode)