from src.orchestrator import Orchestrator


def chat_loop():
    
    print("Cooking Assistant: Hello! I'm your cooking assistant. How can I help you today? (Type 'quit' to exit)")
    chat_history = []
    orchestrator = Orchestrator()  # Instantiate the Orchestrator
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Cooking Assistant: Goodbye! Happy cooking!")
            break
            
        inputs = {
            "messages": chat_history + [("user", user_input)]
        }
        
        for response in orchestrator.stream(inputs, stream_mode="values"):
            message = response["messages"][-1]
      
            tool_used = response.get("tool")
            
            if tool_used:
                print(f"Tool used output hidden for clarity\n")
            else:
                print(message.content, "-"*50,"\n\n")
                
        chat_history = response["messages"]

if __name__ == "__main__":
    chat_loop()