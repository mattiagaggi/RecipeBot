import mlflow
import requests
import time
import os
import sys

# Global variable to store the active run_id
active_run_id = None
mlflow_available = False  # Track if MLflow is available

def setup_mlflow(tracking_uri=None, experiment_id="0"):
    """
    Set up MLflow configuration globally.
    
    - If experiment_id == "0", we'll use the experiment named "Default".
    - Otherwise, we assume it's a valid numeric ID and call mlflow.set_experiment(experiment_id=<ID>).
    """
    global active_run_id, mlflow_available
    
    # 1) Resolve the MLflow Tracking URI (priority: env var -> function arg -> default)
    # For local development, default to a localhost URI if not specified
    in_kubernetes = os.environ.get("KUBERNETES_SERVICE_HOST") is not None
    default_uri = "http://localhost:5000" if not in_kubernetes else "http://mlflow:5002"
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI") or tracking_uri or default_uri
    print(f"Setting MLflow tracking URI to: {tracking_uri}")
    
    # Adjust startup delay based on environment
    if in_kubernetes and os.environ.get("MLFLOW_STARTUP_DELAY"):
        delay = int(os.environ.get("MLFLOW_STARTUP_DELAY", "10"))
        print(f"In Kubernetes: waiting {delay} seconds for MLflow to be ready...")
        time.sleep(delay)
    
    try:
        # 2) Configure tracking URI once
        mlflow.set_tracking_uri(tracking_uri)
        print(f"MLflow tracking URI set to: {tracking_uri}")
        
        # 3) Set artifact location based on environment
        if in_kubernetes:
            artifact_location = os.environ.get("MLFLOW_ARTIFACT_LOCATION", "file://mlflow/artifacts")
            print(f"Running in Kubernetes. Using artifact location: {artifact_location}")
        else:
            # When not in Kubernetes, use a local directory in the current working directory
            artifact_location = os.environ.get("MLFLOW_ARTIFACT_LOCATION", os.path.join(os.getcwd(), "mlflow-artifacts"))
            print(f"Not running in Kubernetes. Using local artifact location: {artifact_location}")
            # Create the directory if it doesn't exist
            try:
                os.makedirs(artifact_location, exist_ok=True)
                print(f"Created artifact directory: {artifact_location}")
            except Exception as e:
                print(f"Warning: Failed to create artifact directory: {str(e)}")
        
        # 4) Quick connectivity check with retries for better reliability
        max_retries = 5  # Increased from 3
        retry_delay = 3  # Increased from 2
        connected = False
        
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt+1}/{max_retries} to connect to MLflow at {tracking_uri}")
                # First try the base URL which should return 200
                response = requests.get(tracking_uri, timeout=10)  # Increased timeout
                
                if response.status_code == 200:
                    print(f"Successfully connected to MLflow UI at {tracking_uri}")
                    
                    # Then try an API endpoint to verify API access
                    try:
                        api_url = f"{tracking_uri}/api/2.0/mlflow/experiments/list"
                        print(f"Testing MLflow API at {api_url}")
                        api_response = requests.get(api_url, timeout=10)
                        
                        # 200 means success, 400 might mean it needs parameters but API exists
                        if api_response.status_code in [200, 400]:
                            print(f"MLflow API is accessible (status: {api_response.status_code})")
                            mlflow_available = True
                            connected = True
                            break
                        else:
                            print(f"Warning: MLflow API returned unexpected status: {api_response.status_code}")
                    except Exception as api_err:
                        print(f"Error testing MLflow API: {str(api_err)}")
                else:
                    print(f"Warning: MLflow base URL returned status code {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error: {str(e)}")
                # Try DNS lookup
                try:
                    import socket
                    hostname = tracking_uri.split("//")[1].split(":")[0]
                    print(f"Trying DNS lookup for {hostname}...")
                    ip = socket.gethostbyname(hostname)
                    print(f"DNS lookup for {hostname}: {ip}")
                except Exception as dns_err:
                    print(f"DNS lookup failed: {str(dns_err)}")
            except Exception as e:
                print(f"Error connecting to MLflow (attempt {attempt+1}/{max_retries}): {str(e)}")
            
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay += 2  # Progressive backoff
        
        if not connected:
            print("MLflow tracking will be disabled, but execution will continue.")
            mlflow_available = False
            return None
        
        # 5) Try to set up the MLflow experiment and run
        print("Attempting to set up MLflow experiment and run...")
        
        if experiment_id == "0":
            # If "0", we interpret that as wanting the named "Default" experiment.
            mlflow.set_experiment(experiment_name="Default")
        else:
            # Otherwise assume it's a valid numeric experiment ID
            mlflow.set_experiment(experiment_id=experiment_id)
        
        try:
            # Optionally enable langchain autolog
            mlflow.langchain.autolog()
        except Exception as e:
            print(f"Warning: Failed to set up langchain autolog: {str(e)}")
        
        try:
            # Start a run if none is active
            if not mlflow.active_run():
                print("Starting MLflow run...")
                mlflow.start_run()
            global active_run_id
            active_run_id = mlflow.active_run().info.run_id
            print(f"MLflow run started with ID: {active_run_id}")
        except Exception as e:
            print(f"Warning: Failed to start MLflow run: {str(e)}")
            active_run_id = None
        
        return active_run_id
    
    except Exception as e:
        print(f"WARNING: MLflow setup failed: {e}", file=sys.stderr)
        mlflow_available = False
        return None

def get_active_run_id():
    """Get the current active MLflow run ID."""
    global active_run_id
    return active_run_id

def is_mlflow_available():
    """Check if MLflow is available for logging."""
    global mlflow_available
    return mlflow_available

def log_metric_safely(key, value):
    """Log a metric to MLflow only if available."""
    if is_mlflow_available() and mlflow.active_run():
        try:
            mlflow.log_metric(key, value)
            return True
        except Exception as e:
            print(f"Warning: Failed to log metric '{key}': {e}")
    return False

def log_param_safely(key, value):
    """Log a parameter to MLflow only if available."""
    if is_mlflow_available() and mlflow.active_run():
        try:
            mlflow.log_param(key, value)
            return True
        except Exception as e:
            print(f"Warning: Failed to log parameter '{key}': {e}")
    return False

def log_text_safely(text, artifact_file):
    """Log text to MLflow only if available."""
    if is_mlflow_available() and mlflow.active_run():
        try:
            mlflow.log_text(text, artifact_file)
            return True
        except Exception as e:
            print(f"Warning: Failed to log text to '{artifact_file}': {e}")
    return False

def test_mlflow_connection():
    """Test connection to MLflow server with detailed error reporting."""
    tracking_uri = mlflow.get_tracking_uri()
    max_retries = 5
    retry_interval = 10  # seconds
    
    print(f"Testing connection to MLflow at {tracking_uri}")
    
    for i in range(max_retries):
        try:
            print(f"Attempt {i+1}: Connecting to {tracking_uri}...")
            # Try a simple API call to check if MLflow is responding
            response = requests.get(f"{tracking_uri}/api/2.0/mlflow/experiments/list", timeout=5)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                print(f"Successfully connected to MLflow at {tracking_uri}")
                return True
            else:
                print(f"MLflow server returned non-200 status: {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {str(e)}")
            # Try DNS lookup
            try:
                import socket
                hostname = tracking_uri.split("//")[1].split(":")[0]
                print(f"Trying DNS lookup for {hostname}...")
                ip = socket.gethostbyname(hostname)
                print(f"DNS lookup for {hostname}: {ip}")
            except Exception as dns_err:
                print(f"DNS lookup failed: {str(dns_err)}")
        except Exception as e:
            print(f"Attempt {i+1}/{max_retries} failed: {type(e).__name__}: {str(e)}")
        
        if i < max_retries - 1:
            print(f"Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
    
    print(f"Failed to connect to MLflow after {max_retries} attempts")
    return False
