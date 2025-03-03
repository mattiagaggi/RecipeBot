import mlflow

# Global variable to store the active run_id
active_run_id = None

def setup_mlflow(tracking_uri="http://127.0.0.1:5001", experiment_id="0"):
    """Set up MLflow configuration globally."""
    global active_run_id
    
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_id=experiment_id)
    mlflow.langchain.autolog()
    
    # Create a new run if none is active
    if not mlflow.active_run():
        mlflow.start_run()
    
    # Store the active run ID globally
    active_run_id = mlflow.active_run().info.run_id
    
    # Return the active run ID for reference
    return active_run_id

def get_active_run_id():
    """Get the current active MLflow run ID."""
    global active_run_id
    return active_run_id