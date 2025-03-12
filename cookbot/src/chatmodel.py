import random
import numpy as np
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

class ChatModel:
    def __init__(self) -> None:
        # Set seeds for different libraries
        random.seed(0)
        np.random.seed(0)
        
        # Initialize the model
        self.model = ChatOpenAI(model="gpt-4o-mini", seed=0)

