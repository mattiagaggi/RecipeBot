from src.orchestrator import Orchestrator
from src.mlflow_config import setup_mlflow, test_mlflow_connection, test_mlflow_connection_detailed
from src.session_manager import SessionManager
import mlflow
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse
import sys
import time
import platform
from urllib.parse import parse_qs
from src.prompts import SYSTEM_PROMPT

# Enable MLflow autologging for all supported libraries
try:
    mlflow.autolog()
    print("MLflow autologging enabled")
except Exception as e:
    print(f"Warning: Failed to enable MLflow autologging: {e}")

# Set up MLflow globally
try:
    # Add detailed connection test before setup
    print("\n=== TESTING MLFLOW CONNECTION BEFORE SETUP ===")
    test_mlflow_connection()
    
    # MLflow setup is now handled in the setup_mlflow function
    # with proper environment detection and configurable delays
    run_id = setup_mlflow()
    if run_id:
        print(f"MLflow tracking active with run_id: {run_id}")
        
        # Add detailed connection test after setup
        print("\n=== TESTING MLFLOW CONNECTION AFTER SETUP ===")
        test_mlflow_connection_detailed()
        
        # Log basic system info
        mlflow.log_param("python_version", platform.python_version())
        mlflow.log_param("system_platform", platform.platform())
        mlflow.log_param("app_start_time", time.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        print("MLflow tracking is disabled, but application will continue")
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
    session_manager = SessionManager()
    
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
                    <button type="button" id="reset-session">Reset Session</button>
                </form>
                
                <script>
                    const form = document.getElementById('chat-form');
                    const input = document.getElementById('user-input');
                    const chatHistory = document.getElementById('chat-history');
                    let sessionId;

                    // Always create a new session when the page loads
                    fetch('/create_session')
                        .then(response => response.json())
                        .then(data => {
                            sessionId = data.session_id;
                            localStorage.setItem('cookbot_session_id', sessionId);
                            console.log('Created new session:', sessionId);
                        })
                        .catch(error => {
                            console.error('Error creating session:', error);
                            chatHistory.innerHTML += `<p><strong>Error:</strong> Failed to create session</p>`;
                        });

                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const message = input.value;
                        if (!message) return;
                        
                        // Display user message
                        chatHistory.innerHTML += `<p><strong>You:</strong> ${message}</p>`;
                        input.value = '';
                        
                        try {
                            // Call the API
                            const response = await fetch('/chat', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                                body: `message=${encodeURIComponent(message)}&session_id=${encodeURIComponent(sessionId)}`
                            });
                            
                            if (response.ok) {
                                const data = await response.json();
                                chatHistory.innerHTML += `<p><strong>Cooking Assistant:</strong> ${data.response}</p>`;
                            } else {
                                chatHistory.innerHTML += `<p><strong>Error:</strong> Failed to get response</p>`;
                            }
                        } catch (error) {
                            console.error('Error during fetch:', error);
                            chatHistory.innerHTML += `<p><strong>Error:</strong> Network error or server not responding</p>`;
                        }
                        
                        // Scroll to bottom
                        chatHistory.scrollTop = chatHistory.scrollHeight;
                    });
                </script>
            </body>
            </html>
            '''
            self.wfile.write(html.encode())
        elif self.path == '/create_session':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            session_id = self.session_manager.create_session()
            
            # Append the system prompt with the appropriate role
            system_message = {"role": "system", "content": SYSTEM_PROMPT}
            self.session_manager.update_session(session_id, [system_message])
            
            response_data = {
                "session_id": session_id
            }
            self.wfile.write(json.dumps(response_data).encode())
        elif self.path == '/reset_session':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parse URL-encoded data
            params = parse_qs(post_data)
            session_id = params.get('session_id', [''])[0]
            
            if not session_id:
                self.send_response(400)
                self.end_headers()
                return
            
            # Delete the existing session
            self.session_manager.delete_session(session_id)
            
            # Create a new session
            new_session_id = self.session_manager.create_session()
            
            # Append the system prompt with the appropriate role
            system_message = {"role": "system", "content": SYSTEM_PROMPT}
            self.session_manager.update_session(new_session_id, [system_message])
            
            # Construct the response data
            response_data = {
                "session_id": new_session_id
            }

            # Send the response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parse URL-encoded data
            params = parse_qs(post_data)
            
            user_input = params.get('message', [''])[0]
            session_id = params.get('session_id', [''])[0]
            
            if not user_input or not session_id:
                self.send_response(400)
                self.end_headers()
                return
            
            # Get existing chat history or create new session
            chat_history = self.session_manager.get_session(session_id)
            if chat_history is None:
                session_id = self.session_manager.create_session()
                chat_history = []
            
            # Process the message and capture the LLM response
            inputs = {
                "messages": chat_history + [("user", user_input)]
            }
            
            response_content = ""
            for response in self.orchestrator.stream(inputs, stream_mode="values"):
                message = response["messages"][-1]
                response_content = message.content  # Capture the LLM's response
            
            # Update the session with new chat history and LLM response
            self.session_manager.update_session(session_id, response["messages"], response_content)
            
            # Construct the response data
            response_data = {
                "response": response_content,  # Include the LLM response here
                "session_id": session_id
            }

            # Send the response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
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