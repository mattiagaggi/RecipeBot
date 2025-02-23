from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

class ChatModel:
    def __init__(self) -> None:
        self.model = ChatOpenAI(model="gpt-4o-mini")

