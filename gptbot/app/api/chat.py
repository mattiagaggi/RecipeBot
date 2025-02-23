from fastapi import APIRouter, HTTPException
from app.models.chat_models import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.utils.session_manager import SessionManager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

chat_service = ChatService()
session_manager = SessionManager()

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest):
    """
    Endpoint to handle user chat requests.
    If session_id is not provided, we create a new one.
    """
    try:
        # 1. Check if a session was provided; create one if not
        session_id = payload.session_id or session_manager.create_session()
        # 2. Retrieve existing conversation history from memory
        session_history_ids = session_manager.get_session(session_id)
        # 3. Generate the new conversation and the bot's response
        full_ids, response_text = chat_service.generate_response(payload.message, session_history_ids)
        # 4. Store/Update the entire conversation in the session
        #    so the next turn can build on it.
        #    We overwrite the session with the full (bot_input + bot_output) tokens.
        session_manager.update_session(session_id, full_ids)
        # 5. Return the newly generated response
        return ChatResponse(
            response=response_text,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}")
        # Try to recover
        raise HTTPException(status_code=500, detail=f"Internal Server Error")
