from typing import Dict, List
import uuid
import gc
from datetime import datetime, timedelta
from app.config.config import Settings

class SessionManager:
    def __init__(self):
        """Initialize the session manager with storage and configuration."""
        self.settings = Settings()
        # Key: session_id, Value: entire conversation as a list of token IDs
        self._storage: Dict[str, List[int]] = {}
        # Tracks last access time for each session
        self._timestamps: Dict[str, datetime] = {}
        # Session timeout calculated from config
        self._timeout = timedelta(minutes=self.settings.SESSION_TIMEOUT_MINUTES)

    def create_session(self) -> str:
        """Create a new chat session with a unique ID."""
        session_id = str(uuid.uuid4())
        self._storage[session_id] = []
        return session_id

    def get_session(self, session_id: str) -> List[int]:
        """Retrieve the conversation history for a given session ID."""
        return self._storage.get(session_id)

    def update_session(self, session_id: str, new_full_ids: List[int]) -> None:
        """
        Update a session with new conversation history and refresh its timestamp.
        Triggers cleanup periodically based on configured interval.
        """
        self._storage[session_id] = new_full_ids
        self._timestamps[session_id] = datetime.now()
        if len(self._storage) % self.settings.SESSION_CLEANUP_INTERVAL == 0:
            self.cleanup_old_sessions()

    def cleanup_old_sessions(self) -> None:
        """Remove expired sessions based on configured timeout."""
        current_time = datetime.now()
        expired_sessions = [
            sid for sid, timestamp in self._timestamps.items()
            if current_time - timestamp > self._timeout
        ]
        for sid in expired_sessions:
            self._storage.pop(sid, None)
            self._timestamps.pop(sid, None)
        gc.collect()

    @property
    def active_sessions_count(self) -> int:
        """Return the number of active sessions."""
        return len(self._storage)


