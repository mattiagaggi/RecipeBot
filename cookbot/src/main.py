from src.orchestrator import Orchestrator
from src.mlflow_config import setup_mlflow
import mlflow

# Set up MLflow globally
run_id = setup_mlflow()
print(f"MLflow tracking active with run_id: {run_id}")

def chat_loop():
    print("Cooking Assistant: Hello! I'm your cooking assistant. How can I help you today? (Type 'quit' to exit)")
    chat_history = []
    orchestrator = Orchestrator()  # Instantiate the Orchestrator
    
    try:
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
                print(message.content, "-"*50,"\n\n")
                    
            chat_history = response["messages"]
    finally:
        # End the MLflow run when exiting the chat loop
        if mlflow.active_run():
            mlflow.end_run()

if __name__ == "__main__":
    chat_loop()