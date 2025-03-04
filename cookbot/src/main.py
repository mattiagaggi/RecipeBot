from src.orchestrator import Orchestrator
from src.mlflow_config import setup_mlflow
import mlflow
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse
import sys
import time

# Set up MLflow globally
try:
    # Add a slight delay to ensure MLflow API is fully available
    print("Waiting 10 seconds for MLflow to be fully ready...")
    time.sleep(30)
    
    run_id = setup_mlflow()
    print(f"MLflow tracking active with run_id: {run_id}")
except Exception as e:
    print(f"Warning: MLflow setup failed: {e}")
    run_id = None

# For debugging purposes
print(f"Environment variables:")
for k, v in os.environ.items():
    if "KUBE" in k.upper():
        print(f"  {k}: {v}")

# Force web mode by default in Kubernetes, allow override with env var
FORCE_CLI = os.environ.get('FORCE_CLI', '').lower() in ('true', '1', 't')
IN_KUBERNETES = os.environ.get('KUBERNETES_SERVICE_HOST') is not None

# Print debug info
print(f"KUBERNETES_SERVICE_HOST: {os.environ.get('KUBERNETES_SERVICE_HOST')}")
print(f"IN_KUBERNETES detected as: {IN_KUBERNETES}")
print(f"FORCE_CLI: {FORCE_CLI}")

# More explicit logging to debug the environment
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")
try:
    print(f"src directory contents: {os.listdir('./src')}")
except Exception as e:
    print(f"Could not list src directory: {e}")

class ChatHandler(BaseHTTPRequestHandler):
    orchestrator = Orchestrator()
    chat_history = []
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Simple HTML form
            html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Cooking Assistant</title>
                <style>
                    body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
                    #chat-history { border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: scroll; margin-bottom: 10px; }
                    #user-input { width: 80%; padding: 8px; }
                    button { padding: 8px 15px; }
                </style>
            </head>
            <body>
                <h1>Cooking Assistant</h1>
                <div id="chat-history">
                    <p><strong>Cooking Assistant:</strong> Hello! I'm your cooking assistant. How can I help you today?</p>
                </div>
                <form id="chat-form">
                    <input type="text" id="user-input" placeholder="Type your message here...">
                    <button type="submit">Send</button>
                </form>
                
                <script>
                    const form = document.getElementById('chat-form');
                    const input = document.getElementById('user-input');
                    const chatHistory = document.getElementById('chat-history');
                    
                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const message = input.value;
                        if (!message) return;
                        
                        // Display user message
                        chatHistory.innerHTML += `<p><strong>You:</strong> ${message}</p>`;
                        input.value = '';
                        
                        // Call the API
                        const response = await fetch('/chat', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                            body: `message=${encodeURIComponent(message)}`
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            chatHistory.innerHTML += `<p><strong>Cooking Assistant:</strong> ${data.response}</p>`;
                        } else {
                            chatHistory.innerHTML += `<p><strong>Error:</strong> Failed to get response</p>`;
                        }
                        
                        // Scroll to bottom
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    });
                </script>
            </body>
            </html>
            '''
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            user_input = params.get('message', [''])[0]
            if not user_input:
                self.send_response(400)
                self.end_headers()
                return
            
            # Process the message
            inputs = {
                "messages": self.chat_history + [("user", user_input)]
            }
            
            response_content = ""
            for response in self.orchestrator.stream(inputs, stream_mode="values"):
                message = response["messages"][-1]
                response_content = message.content
            
            self.chat_history = response["messages"]
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response_data = {
                "response": response_content
            }
            self.wfile.write(json.dumps(response_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

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

def start_http_server():
    try:
        server = HTTPServer(('0.0.0.0', 9090), ChatHandler)
        print(f"Server started at http://0.0.0.0:9090")
        server.serve_forever()
    except Exception as e:
        print(f"ERROR STARTING SERVER: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    # ALWAYS start the HTTP server when in Kubernetes (or if env var is forced)
    print("Starting HTTP server for Kubernetes environment")
    try:
        # Add a timeout so it doesn't hang forever if there's an issue
        server_thread = threading.Thread(target=start_http_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Keep the main thread alive with periodic heartbeat messages
        while True:
            print("Server heartbeat - still running")
            sys.stdout.flush()  # Force flush stdout 
            threading.Event().wait(60)  # Heartbeat every 60 seconds
    except KeyboardInterrupt:
        print("Server shutting down")
    except Exception as e:
        print(f"Fatal error in main thread: {e}", file=sys.stderr)
        sys.stderr.flush()  # Force flush stderr
        sys.exit(1)
    finally:
        if mlflow.active_run():
            mlflow.end_run()