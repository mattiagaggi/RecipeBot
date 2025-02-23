import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging
from typing import List, Tuple, Optional

from app.config.config import Settings

logger = logging.getLogger(__name__)

class ChatService:
    """
    Service for handling chat interactions with a language model.

    This class encapsulates:
      - Model/tokenizer loading
      - Device configuration (CUDA/MPS/CPU)
      - Parameter setup (history constraints, etc.)
      - Message generation
      - Input/output processing (tokenization, decoding)
    
    Typical usage:
      1. Instantiate the service: `chat_service = ChatService()`.
      2. Call `generate_response(user_message, session_history_ids)` to obtain
         the model's response and updated session history.
    """

    def __init__(self):
        """
        Initialize the ChatService with model, tokenizer, device settings, 
        and other configurations. Raises an Exception if model loading fails.
        """
        self.settings = Settings()
        logger.info(f"Loading model: {self.settings.MODEL_NAME}")
        try:
            self._initialize_model()
            self._setup_device()
            self._configure_parameters()
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

    def _initialize_model(self) -> None:
        """
        Load the tokenizer and the causal language model from the specified 
        model name in settings. Uses half-precision (float16) for memory efficiency.
        """
        self.tokenizer = AutoTokenizer.from_pretrained(self.settings.MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.settings.MODEL_NAME,
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16
        )

    def _setup_device(self) -> None:
        """
        Configure the device for model inference. If CUDA is available, use GPU;
        otherwise check if MPS (Apple Silicon) is available; fallback to CPU 
        if neither is found. Moves model to the chosen device.
        """
        if torch.cuda.is_available():
            self.device = 'cuda'
        elif torch.backends.mps.is_available():
            self.device = 'mps'
        else:
            self.device = 'cpu'
        self.model = self.model.to(self.device)
        logger.info(f"Model loaded successfully on {self.device}")

    def _configure_parameters(self) -> None:
        """
        Set up model-specific parameters and constraints, including:
          - max_history: maximum tokens to preserve from past conversation
          - max_context_length: maximum allowed input length from model config
          - space_for_generation: space to reserve for new tokens during generation
        """
        self.max_history = self.settings.MAX_HISTORY
        self.max_context_length = self._get_max_context_length()
        self.space_for_generation = self.settings.SPACE_FOR_GENERATION

    def _get_max_context_length(self) -> int:
        """
        Determine the maximum context length supported by the model by checking
        known configuration attributes (max_position_embeddings, n_positions, 
        max_sequence_length). Defaults to 2048 if none are found.
        
        Returns:
            int: The maximum context length for the model.
        """
        return getattr(
            self.model.config, 'max_position_embeddings',
            getattr(self.model.config, 'n_positions',
                getattr(self.model.config, 'max_sequence_length', 2048))
        )

    def generate_response(
        self, 
        user_message: str, 
        session_history_ids: Optional[List[int]] = None, 
        do_sample: bool = True
    ) -> Tuple[List[int], str]:
        """
        Generate a response to the user's message, optionally including the
        provided conversation history as token IDs.

        Args:
            user_message (str): The input message from the user.
            session_history_ids (List[int], optional): Previous conversation
                history as token IDs. Defaults to an empty list if not provided.
            do_sample (bool, optional): Whether to use sampling (temperature, 
                randomness) in generation. If False, uses greedy-like approach.

        Returns:
            Tuple[List[int], str]: A tuple containing:
              - The updated conversation token IDs (history + new response)
              - The generated response text
        """
        session_history_ids = session_history_ids or []

        # Prepare input context (history + new user message)
        model_input = self._prepare_input(user_message, session_history_ids)
        attention_mask = torch.ones_like(model_input)

        # Generate output tokens from the model
        output_ids = self._generate_output(model_input, attention_mask, do_sample)

        # Process output into final conversation IDs and decoded text
        return self._process_output(output_ids, model_input.shape[-1])

    def _prepare_input(self, user_message: str, session_history_ids: List[int]) -> torch.Tensor:
        """
        Prepare the input context for the model by:
          1. Encoding the new user message with proper DialoGPT formatting
          2. Truncating existing history if necessary
          3. Concatenating the history tokens with the new message tokens
        """
        # DialoGPT expects just the raw message without prefixes
        new_input_ids = self.tokenizer.encode(
            user_message + self.tokenizer.eos_token,  # Add EOS token but no prefix
            return_tensors='pt'
        ).to(self.device)

        # Ensure there's space for new tokens by possibly truncating history
        available_length = self.max_context_length - new_input_ids.shape[1] - self.space_for_generation
        if len(session_history_ids) > available_length:
            session_history_ids = session_history_ids[-available_length:]

        # Rest of the method remains the same
        history_tensor = (torch.tensor([session_history_ids], dtype=torch.long).to(self.device) 
                          if session_history_ids else None)
        if history_tensor is not None:
            combined_input = torch.cat([history_tensor, new_input_ids], dim=-1)
        else:
            combined_input = new_input_ids

        return combined_input

    def _generate_output(
        self, 
        model_input: torch.Tensor, 
        attention_mask: torch.Tensor, 
        do_sample: bool
    ) -> torch.Tensor:
        """
        Generate new output tokens based on the prepared model input. 

        Args:
            model_input (torch.Tensor): The full model input context (history + new message).
            attention_mask (torch.Tensor): Mask for attention (same shape as model_input).
            do_sample (bool): Whether to sample (temperature-based) or do greedy-like generation.

        Returns:
            torch.Tensor: The generated token IDs (including the original model_input).
        """
        max_new_tokens = min(
            self.settings.MAX_LENGTH,  # Use configured max length
            self.max_context_length - model_input.shape[1]
        )

        return self.model.generate(
            model_input,
            attention_mask=attention_mask,
            max_new_tokens=max_new_tokens,
            min_length=self.settings.MIN_LENGTH,
            pad_token_id=self.tokenizer.eos_token_id,
            do_sample=do_sample,
            temperature=self.settings.TEMPERATURE if do_sample else 1.0,
            top_p=self.settings.TOP_P,
            num_beams=self.settings.BEAMS,
            early_stopping=True,  # Changed to True to stop when EOS is generated
            no_repeat_ngram_size=self.settings.NO_REPEAT_NGRAM_SIZE
        )

    def _process_output(self, output_ids: torch.Tensor, start_idx: int) -> Tuple[List[int], str]:
        """
        Extract the newly generated tokens from the model output, decode them 
        into text, and return both the full updated conversation token IDs and 
        the textual response.

        Args:
            output_ids (torch.Tensor): The model output token IDs.
            start_idx (int): The index at which new tokens begin (i.e., length 
                of the input context).

        Returns:
            Tuple[List[int], str]: 
              - A list of full conversation token IDs
              - The generated response text (stripped of special tokens/spaces).
        """
        full_ids = output_ids[0].cpu().tolist()  # Flatten from batch
        new_tokens = full_ids[start_idx:]
        response_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return full_ids, response_text.strip()
