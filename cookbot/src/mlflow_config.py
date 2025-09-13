import mlflow
import requests
import time
import os
import sys
import json
from typing import Optional, Union, Dict, Any, Tuple

# Global variables
active_run_id = None
mlflow_available = False

# Constants
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2


def is_kubernetes_environment() -> bool:
    """Determine if we're running in a Kubernetes environment."""
    return os.environ.get("KUBERNETES_SERVICE_HOST") is not None

def is_docker_environment() -> bool:
    """Determine if we're running in a Docker environment."""
    return os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "true"

def get_tracking_uri() -> str:
    """Determine the appropriate MLflow tracking URI based on environment."""
    in_kubernetes = is_kubernetes_environment()
    in_docker = is_docker_environment()
    
    if in_kubernetes:
        default_uri = "http://mlflow:5002"
    elif in_docker:
        default_uri = "http://mlflow:5002"
    else:
        default_uri = "http://localhost:5000"
    
    return os.environ.get("MLFLOW_TRACKING_URI", default_uri)

def get_artifact_location() -> str:
    """Determine the appropriate artifact location based on environment."""
    if is_kubernetes_environment():
        return os.environ.get("MLFLOW_ARTIFACT_LOCATION", "file:/mlflow/artifacts")
    else:
        # Local development uses a directory in the current working directory
        return os.environ.get("MLFLOW_ARTIFACT_LOCATION", "file:///mlflow/artifacts")

def ensure_artifact_directory(artifact_location: str) -> bool:
    """Ensure the artifact directory exists for local development."""
    if not is_kubernetes_environment() and not artifact_location.startswith("file:"):
        try:
            os.makedirs(artifact_location, exist_ok=True)
            print(f"Created artifact directory: {artifact_location}")
            return True
        except Exception as e:
            print(f"Warning: Failed to create artifact directory: {str(e)}")
            return False
    return True

def test_mlflow_connectivity(tracking_uri: str, max_attempts: int = 5) -> bool:
    """Test connectivity to MLflow server with retries."""
    retry_delay = RETRY_DELAY
    
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt+1}/{max_attempts} to connect to MLflow at {tracking_uri}")
            
            # First check if the MLflow UI is accessible
            response = requests.get(tracking_uri, timeout=DEFAULT_TIMEOUT)
            if response.status_code != 200:
                print(f"Warning: MLflow UI returned status code {response.status_code}")
                raise ConnectionError(f"MLflow UI returned status code {response.status_code}")
                
            print(f"Successfully connected to MLflow UI at {tracking_uri}")
            
            # Use the correct API endpoint with required parameters
            api_url = f"{tracking_uri}/api/2.0/mlflow/experiments/search"
            print(f"Testing MLflow API at {api_url}")
            
            # Add the required max_results parameter
            params = {"max_results": 10}
            api_response = requests.get(api_url, params=params, timeout=DEFAULT_TIMEOUT)
            
            # 200 means success
            if api_response.status_code == 200:
                print(f"MLflow API is accessible (status: {api_response.status_code})")
                return True
            else:
                print(f"Warning: MLflow API returned unexpected status: {api_response.status_code}")
                print(f"Response content: {api_response.text}")
                # If it's a 400 with a specific error about parameters, that's still a success
                # because it means the API endpoint exists
                if api_response.status_code == 400 and "INVALID_PARAMETER_VALUE" in api_response.text:
                    print("API endpoint exists but requires different parameters - this is acceptable")
                    return True
                else:
                    raise ConnectionError(f"MLflow API returned unexpected status: {api_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Connection error on attempt {attempt+1}: {str(e)}")
        except Exception as e:
            print(f"Unexpected error on attempt {attempt+1}: {str(e)}")
        
        if attempt < max_attempts - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay += 2  # Progressive backoff
    
    return False

def setup_experiment(experiment_id: str = "0") -> Optional[str]:
    """Set up the MLflow experiment."""
    try:
        if experiment_id == "0":
            # If "0", we interpret that as wanting the named "Default" experiment
            mlflow.set_experiment(experiment_name="Default")
            print("Using 'Default' experiment")
        else:
            # Otherwise assume it's a valid numeric experiment ID
            mlflow.set_experiment(experiment_id=experiment_id)
            print(f"Using experiment ID: {experiment_id}")
        
        # Try to enable langchain autolog if available
        try:
            mlflow.langchain.autolog()
            print("Langchain autolog enabled")
        except Exception as e:
            print(f"Note: Langchain autolog not available: {str(e)}")
        
        # Start a run if none is active
        if not mlflow.active_run():
            print("Starting new MLflow run...")
            mlflow.start_run()
        
        run_id = mlflow.active_run().info.run_id
        print(f"Active MLflow run ID: {run_id}")
        return run_id
    
    except Exception as e:
        print(f"Error setting up MLflow experiment: {str(e)}")
        return None

def setup_mlflow(tracking_uri: Optional[str] = None, experiment_id: str = "0") -> Optional[str]:
    """
    Set up MLflow configuration globally.
    
    Args:
        tracking_uri: Optional MLflow tracking URI (overrides environment variable)
        experiment_id: Experiment ID or "0" for the default experiment
        
    Returns:
        The active run ID if setup was successful, None otherwise
    """
    global active_run_id, mlflow_available
    
    try:
        # 1. Determine and set tracking URI
        resolved_tracking_uri = tracking_uri or get_tracking_uri()
        print(f"Setting MLflow tracking URI to: {resolved_tracking_uri}")
        mlflow.set_tracking_uri(resolved_tracking_uri)
        
        # 2. Handle startup delay for Kubernetes
        if is_kubernetes_environment() and os.environ.get("MLFLOW_STARTUP_DELAY"):
            delay = int(os.environ.get("MLFLOW_STARTUP_DELAY", "10"))
            print(f"In Kubernetes: waiting {delay} seconds for MLflow to be ready...")
            time.sleep(delay)
        
        # 3. Set up artifact location
        artifact_location = get_artifact_location()
        print(f"Using artifact location: {artifact_location}")
        ensure_artifact_directory(artifact_location)
        os.environ["MLFLOW_ARTIFACT_LOCATION"] = artifact_location
        
        # 4. Test connectivity to MLflow
        if not test_mlflow_connectivity(resolved_tracking_uri):
            print("MLflow tracking will be disabled, but execution will continue.")
            mlflow_available = False
            return None
        
        # 5. Set up experiment and start run
        mlflow_available = True
        active_run_id = setup_experiment(experiment_id)
        return active_run_id
        
    except Exception as e:
        print(f"WARNING: MLflow setup failed: {e}", file=sys.stderr)
        mlflow_available = False
        return None

def get_active_run_id() -> Optional[str]:
    """Get the current active MLflow run ID."""
    global active_run_id
    return active_run_id

def is_mlflow_available() -> bool:
    """Check if MLflow is available for logging."""
    global mlflow_available
    return mlflow_available

def retry_operation(operation, *args, max_retries: int = MAX_RETRIES, **kwargs) -> Tuple[bool, Any]:
    """
    Retry an operation with exponential backoff.
    
    Args:
        operation: The function to retry
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple of (success, result)
    """
    for attempt in range(max_retries):
        try:
            result = operation(*args, **kwargs)
            return True, result
        except BrokenPipeError as e:
            if attempt < max_retries - 1:
                print(f"BrokenPipeError on attempt {attempt+1}, retrying: {str(e)}")
                time.sleep(1 * (attempt + 1))  # Exponential backoff
            else:
                print(f"Failed after {max_retries} attempts: {str(e)}")
                return False, e
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return False, e
    
    return False, None

def log_metric_safely(key: str, value: Union[int, float]) -> bool:
    """Log a metric to MLflow only if available."""
    if not is_mlflow_available():
        print(f"Warning: Cannot log metric '{key}': MLflow not available or no active run")
        return False
        
    try:
        success, _ = retry_operation(mlflow.log_metric, key, value)
        if success:
            print(f"Successfully logged metric '{key}': {value}")
            return True
        print(f"Warning: Failed to log metric '{key}'")
    except Exception as e:
        print(f"Warning: Failed to log metric '{key}': {e}")
    
    return False

def log_param_safely(key: str, value: Any) -> bool:
    """Log a parameter to MLflow only if available."""
    if not is_mlflow_available():
        return False
        
    try:
        success, _ = retry_operation(mlflow.log_param, key, value)
        if success:
            return True
        print(f"Warning: Failed to log parameter '{key}'")
    except Exception as e:
        print(f"Warning: Failed to log parameter '{key}': {e}")
    
    return False

def log_text_safely(text: str, artifact_file: str) -> bool:
    """Log text to MLflow only if available."""
    print(f"Attempting to log text to artifact: {artifact_file}")
    
    if not is_mlflow_available():
        print(f"MLflow not available, skipping text logging for: {artifact_file}")
        return False
        
    try:
        print(f"MLflow available, attempting to log text to: {artifact_file}")
        success, result = retry_operation(mlflow.log_text, text, artifact_file)
        if success:
            print(f"Successfully logged text to artifact: {artifact_file}")
            return True
        print(f"Warning: Failed to log text to '{artifact_file}', result: {result}")
    except Exception as e:
        print(f"Warning: Failed to log text to '{artifact_file}': {e}")
    
    return False

def log_artifact_safely(local_path: str, artifact_path: Optional[str] = None) -> bool:
    """Log an artifact file to MLflow only if available."""
    if not is_mlflow_available() or not mlflow.active_run():
        return False
        
    try:
        if not os.path.exists(local_path):
            print(f"Warning: Cannot log artifact - file does not exist: {local_path}")
            return False
            
        success, _ = retry_operation(mlflow.log_artifact, local_path, artifact_path)
        if success:
            print(f"Successfully logged artifact: {local_path} to {artifact_path or 'root'}")
            return True
        print(f"Warning: Failed to log artifact '{local_path}'")
    except Exception as e:
        print(f"Warning: Failed to log artifact '{local_path}': {e}")
    
    return False

def log_artifacts_safely(local_dir: str, artifact_path: Optional[str] = None) -> bool:
    """Log a directory of artifacts to MLflow only if available."""
    if not is_mlflow_available():
        return False
        
    try:
        if not os.path.exists(local_dir):
            print(f"Warning: Cannot log artifacts - directory does not exist: {local_dir}")
            return False
            
        success, _ = retry_operation(mlflow.log_artifacts, local_dir, artifact_path)
        if success:
            print(f"Successfully logged artifacts from directory: {local_dir} to {artifact_path or 'root'}")
            return True
        print(f"Warning: Failed to log artifacts from directory '{local_dir}'")
    except Exception as e:
        print(f"Warning: Failed to log artifacts from directory '{local_dir}': {e}")
    
    return False

def test_mlflow_connection_detailed() -> bool:
    """Comprehensive test of MLflow connection with detailed diagnostics."""
    tracking_uri = mlflow.get_tracking_uri()
    print(f"\n=== DETAILED MLFLOW CONNECTION TEST ===")
    print(f"MLflow tracking URI: {tracking_uri}")
    print(f"MLflow available: {is_mlflow_available()}")
    print(f"Active run ID: {get_active_run_id()}")
    
    # Test basic connectivity
    try:
        print("\nTesting basic connectivity...")
        response = requests.get(tracking_uri, timeout=DEFAULT_TIMEOUT)
        print(f"MLflow UI response: {response.status_code}")
        
        # Test API access
        api_url = f"{tracking_uri}/api/2.0/mlflow/experiments/list"
        print(f"\nTesting API access at {api_url}...")
        api_response = requests.get(api_url, timeout=DEFAULT_TIMEOUT)
        print(f"API response status: {api_response.status_code}")
        
        if api_response.status_code == 200:
            print("API response content:")
            content = api_response.json()
            print(json.dumps(content, indent=2))
            
        # Test active run
        if mlflow.active_run():
            print(f"\nActive run exists: {mlflow.active_run().info.run_id}")
            
            # Test metric logging
            test_metric_name = "test_metric"
            test_value = time.time() % 100  # Random-ish value
            print(f"\nTesting metric logging with '{test_metric_name}': {test_value}...")
            mlflow.log_metric(test_metric_name, test_value)
            print("Metric logged successfully")
            
            # Test parameter logging
            test_param_name = "test_param"
            test_param_value = f"test_value_{int(time.time())}"
            print(f"\nTesting parameter logging with '{test_param_name}': {test_param_value}...")
            mlflow.log_param(test_param_name, test_param_value)
            print("Parameter logged successfully")
            
            return True
        else:
            print("\nNo active MLflow run!")
            return False
            
    except Exception as e:
        print(f"\nError during detailed MLflow test: {type(e).__name__}: {str(e)}")
        return False

def increment_metric_safely(key: str, value: Union[int, float] = 1) -> bool:
    """
    This function has been modified to only log text about the tool being called,
    without actually incrementing any metrics.
    """
    # Extract the tool name from the metric key (remove _success_count or _error_count suffix)
    tool_name = key.replace("_success_count", "").replace("_error_count", "").replace("_count_total", "")
    
    # Just log that the tool was called
    print(f"Tool called: {tool_name}")
    
    # Don't attempt to log metrics
    return True

def test_mlflow_connection():
    """Simple wrapper around test_mlflow_connectivity with default tracking URI."""
    tracking_uri = get_tracking_uri()
    print(f"Testing MLflow connection to {tracking_uri}")
    return test_mlflow_connectivity(tracking_uri)