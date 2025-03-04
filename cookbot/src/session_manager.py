from typing import Dict, List, Any, Optional, Tuple
import uuid
import gc
from datetime import datetime, timedelta
import os
import mlflow
from src.mlflow_config import is_mlflow_available, get_active_run_id

class SessionManager:
    def __init__(self, timeout_minutes: int = 30, cleanup_interval: int = 10):
        """Initialize the session manager with storage and configuration.
        
        Args:
            timeout_minutes: Number of minutes after which a session expires
            cleanup_interval: Interval for triggering cleanup (every N sessions)
        """
        # Key: session_id, Value: chat history
        self._storage: Dict[str, List[Any]] = {}
        # Tracks last access time for each session
        self._timestamps: Dict[str, datetime] = {}
        # Tracks MLflow run IDs for each session
        self._mlflow_runs: Dict[str, str] = {}
        # Session timeout
        self._timeout = timedelta(minutes=timeout_minutes)
        # Cleanup interval
        self._cleanup_interval = cleanup_interval
        
        # Get timeout from environment if available
        env_timeout = os.environ.get('SESSION_TIMEOUT_MINUTES')
        if env_timeout:
            try:
                self._timeout = timedelta(minutes=int(env_timeout))
                print(f"Using session timeout from environment: {env_timeout} minutes")
            except ValueError:
                print(f"Invalid SESSION_TIMEOUT_MINUTES value: {env_timeout}, using default")

    def create_session(self) -> str:
        """Create a new chat session with a unique ID and associate with MLflow run."""
        session_id = str(uuid.uuid4())
        self._storage[session_id] = []
        self._timestamps[session_id] = datetime.now()
        
        # Create a new MLflow run for this session if MLflow is available
        if is_mlflow_available():
            try:
                # End any existing run first
                if mlflow.active_run():
                    mlflow.end_run()
                
                # Start a new run with session ID in the name
                mlflow.start_run(run_name=f"session_{session_id}")
                run_id = mlflow.active_run().info.run_id
                self._mlflow_runs[session_id] = run_id
                
                # Log the session creation
                mlflow.log_param("session_id", session_id)
                mlflow.log_param("session_created_at", datetime.now().isoformat())
                print(f"Created new MLflow run {run_id} for session {session_id}")
            except Exception as e:
                print(f"Warning: Failed to create MLflow run for session {session_id}: {e}")
        
        return session_id

    def get_session(self, session_id: str) -> Optional[List[Any]]:
        """Retrieve the conversation history for a given session ID and activate its MLflow run."""
        if session_id in self._storage:
            self._timestamps[session_id] = datetime.now()  # Update timestamp on access
            
            # Activate the MLflow run associated with this session
            self._activate_session_run(session_id)
            
            return self._storage.get(session_id)
        return None

    def update_session(self, session_id: str, chat_history: List[Any]) -> None:
        """
        Update a session with new conversation history and refresh its timestamp.
        Triggers cleanup periodically based on configured interval.
        """
        self._storage[session_id] = chat_history
        self._timestamps[session_id] = datetime.now()
        
        # Ensure the correct MLflow run is active
        self._activate_session_run(session_id)
        
        # Log message count to MLflow
        if is_mlflow_available() and mlflow.active_run():
            try:
                mlflow.log_metric("message_count", len(chat_history))
                mlflow.log_metric("last_update_timestamp", datetime.now().timestamp())
            except Exception as e:
                print(f"Warning: Failed to log metrics for session {session_id}: {e}")
        
        if len(self._storage) % self._cleanup_interval == 0:
            self.cleanup_old_sessions()

    def _activate_session_run(self, session_id: str) -> None:
        """Activate the MLflow run associated with this session."""
        if not is_mlflow_available():
            return
            
        try:
            # If we have a run ID for this session
            if session_id in self._mlflow_runs:
                run_id = self._mlflow_runs[session_id]
                
                # If there's an active run but it's not this session's run
                if mlflow.active_run() and mlflow.active_run().info.run_id != run_id:
                    mlflow.end_run()  # End the current run
                    mlflow.start_run(run_id=run_id)  # Start this session's run
                    print(f"Activated existing MLflow run {run_id} for session {session_id}")
                # If there's no active run
                elif not mlflow.active_run():
                    mlflow.start_run(run_id=run_id)
                    print(f"Activated existing MLflow run {run_id} for session {session_id}")
            # If we don't have a run ID for this session but the session exists
            elif session_id in self._storage:
                # Create a new run for this existing session
                mlflow.start_run(run_name=f"session_{session_id}")
                run_id = mlflow.active_run().info.run_id
                self._mlflow_runs[session_id] = run_id
                mlflow.log_param("session_id", session_id)
                mlflow.log_param("session_activated_at", datetime.now().isoformat())
                print(f"Created new MLflow run {run_id} for existing session {session_id}")
        except Exception as e:
            print(f"Warning: Failed to activate MLflow run for session {session_id}: {e}")

    def cleanup_old_sessions(self) -> None:
        """Remove expired sessions based on configured timeout and end their MLflow runs."""
        current_time = datetime.now()
        expired_sessions = [
            sid for sid, timestamp in self._timestamps.items()
            if current_time - timestamp > self._timeout
        ]
        
        for sid in expired_sessions:
            # End the MLflow run for this session if it exists
            if sid in self._mlflow_runs and is_mlflow_available():
                try:
                    run_id = self._mlflow_runs[sid]
                    # Only end the run if it's the active one
                    if mlflow.active_run() and mlflow.active_run().info.run_id == run_id:
                        mlflow.end_run()
                        print(f"Ended MLflow run {run_id} for expired session {sid}")
                except Exception as e:
                    print(f"Warning: Failed to end MLflow run for session {sid}: {e}")
            
            # Remove session data
            self._storage.pop(sid, None)
            self._timestamps.pop(sid, None)
            self._mlflow_runs.pop(sid, None)
        
        if expired_sessions:
            print(f"Cleaned up {len(expired_sessions)} expired sessions")
            gc.collect()

    def get_mlflow_run_id(self, session_id: str) -> Optional[str]:
        """Get the MLflow run ID associated with a session."""
        return self._mlflow_runs.get(session_id)

    @property
    def active_sessions_count(self) -> int:
        """Return the number of active sessions."""
        return len(self._storage) 