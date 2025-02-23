import requests
import sys
import os
import time

# If HOST_NUMBER is not set, default to the service name 'gptbot-api'
host_number = os.getenv("HOST_NUMBER", "gptbot-api")
API_URL = f"http://{host_number}:8000/api"

def wait_for_api_ready():
    health_url = f"http://{host_number}:8000/health"
    while True:
        try:
            response = requests.get(health_url)
            if response.status_code == 200:
                print("API is ready.")
                break
        except requests.exceptions.RequestException:
            print("Waiting for API to be ready...")
        time.sleep(5)  # Wait for 5 seconds before retrying

def main():
    wait_for_api_ready()  # Ensure API is ready before starting

    session_id = None
    print("Welcome to the DialoGPT Chat (via FastAPI)!")
    
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        payload = {"message": user_input}
        if session_id:
            payload["session_id"] = session_id

        try:
            resp = requests.post(f"{API_URL}/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            bot_response = data["response"]
            session_id = data["session_id"]

            print(f"Bot: {bot_response}\n")

        except requests.exceptions.RequestException as e:
            print(f"Error contacting the server: {e}")
            # Instead of exiting, ask if user wants to start a new session
            retry = input("Would you like to start a new session? (y/n): ")
            if retry.lower() == 'y':
                session_id = None
                continue
            else:
                break

if __name__ == "__main__":
    main()
