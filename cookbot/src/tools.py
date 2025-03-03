from langchain_core.tools import tool
from typing import Union
from langchain_core.exceptions import OutputParserException
from src.pydantic_types import Recipe, SearchResults, ErrorResponse
from pydantic import ValidationError
from src.pydantic_types import TranslationOutput, ClarificationOutput, ErrorResponse
from src.tool_functions import adjust_recipe_quantities, clarify_recipe_step, translate_recipe, web_search, create_recipe_from_intent
from src.error_messages import (
    ADJUST_QUANTITIES_GUIDANCE,
    TRANSLATE_RECIPE_GUIDANCE,
    CLARIFY_RECIPE_STEP_GUIDANCE,
    WEB_SEARCH_GUIDANCE,
    CREATE_RECIPE_FROM_INTENT_GUIDANCE
)
import mlflow
from src.mlflow_config import setup_mlflow, get_active_run_id
import json
import uuid
import datetime
from src.prompts import (
    TRANSLATE_RECIPE_PROMPT,
    ADJUST_RECIPE_QUANTITIES_PROMPT,
    CLARIFY_RECIPE_STEP_PROMPT,
    SEARCH_RECIPE_PROMPT,
    CREATE_RECIPE_FROM_INTENT_PROMPT
)



@tool
def adjust_recipe_quantities_tool(recipe: Recipe, adjustment: str) -> Union[Recipe, ErrorResponse]:
    """adjust_recipe_quantities_tool - adjusts the quantities of ingredients in a recipe based on a natural language input.
    Args:
        recipe (Recipe): The recipe object containing ingredients, quantities, units, and steps
        adjustment (str): Natural language description of how to adjust the recipe
            (e.g., "double the recipe", "make it for 6 people instead of 4", "half the portions")
    Returns:
        Adjusted quantities for each ingredient or an error message if validation fails
    """
    call_id = str(uuid.uuid4())[:8]  # Generate a short unique ID for this tool call
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = get_active_run_id()
    tool_name = "adjust_recipe_quantities"
    
    # Prepare input data with prompt included
    input_data = {
        "recipe": recipe.dict(),
        "adjustment": adjustment,
        "prompt_template": ADJUST_RECIPE_QUANTITIES_PROMPT
    }
    
    # Log tool call inputs to MLflow with run_id context
    mlflow.log_param(f"tool_call_{call_id}", "adjust_recipe_quantities_tool")
    mlflow.log_text(json.dumps(input_data, indent=2), f"{timestamp}_{tool_name}_input_{call_id}.json")
    
    try:
        result = adjust_recipe_quantities(recipe, adjustment)
        # Log success result to MLflow
        mlflow.log_metric(f"tool_success_{call_id}", 1)
        # Log the result as an artifact
        result_json = json.dumps(result.dict(), indent=2)
        mlflow.log_text(result_json, f"{timestamp}_{tool_name}_output_{call_id}.json")
        return result
    except ValidationError as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=ADJUST_QUANTITIES_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response
    except OutputParserException as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=ADJUST_QUANTITIES_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response

@tool
def translate_recipe_tool(recipe: Recipe, language: str) -> Union[TranslationOutput, ErrorResponse]:
    """translate_recipe_tool-translates a recipe's ingredients and steps into the specified language.

    Args:
        recipe (Recipe): The recipe to translate
        language (str): Target language for translation

    Returns:
        Translated ingredients and steps as a list of strings or an error message if validation fails
    """
    call_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tool_name = "translate_recipe"
    
    # Prepare input data with prompt included
    input_data = {
        "recipe": recipe.dict(),
        "language": language,
        "prompt_template": TRANSLATE_RECIPE_PROMPT
    }
    
    # Log tool call inputs to MLflow
    mlflow.log_param(f"tool_call_{call_id}", "translate_recipe_tool")
    mlflow.log_text(json.dumps(input_data, indent=2), f"{timestamp}_{tool_name}_input_{call_id}.json")
    
    try:
        result = translate_recipe(recipe, language)
        # Log success result to MLflow
        mlflow.log_metric(f"tool_success_{call_id}", 1)
        mlflow.log_text(json.dumps(result.dict(), indent=2), f"{timestamp}_{tool_name}_output_{call_id}.json")
        return result
    except ValidationError as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=TRANSLATE_RECIPE_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}_{language}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}_{language}.json")
        return error_response
    except OutputParserException as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=TRANSLATE_RECIPE_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}_{language}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}_{language}.json")
        return error_response

@tool
def clarify_recipe_step_tool(recipe: Recipe, clarification_request: str) -> Union[ClarificationOutput, ErrorResponse]:
    """clarify_recipe_step_tool - analyzes a recipe and provides detailed clarifications for any steps that might be unclear or need additional explanation.

    Args:
        recipe (Recipe): A Recipe object containing ingredients, quantities, units, and preparation steps
        user_clarification_request (str): A user request for clarification of a specific step in the recipe

    Returns:
        ClarificationOutput: A detailed explanation of any steps that need clarification, including cooking techniques, 
    """
    call_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tool_name = "clarify_recipe_step"
    
    # Prepare input data with prompt included
    input_data = {
        "recipe": recipe.dict(),
        "clarification_request": clarification_request,
        "prompt_template": CLARIFY_RECIPE_STEP_PROMPT
    }
    
    # Log tool call inputs to MLflow
    mlflow.log_param(f"tool_call_{call_id}", "clarify_recipe_step_tool")
    mlflow.log_text(json.dumps(input_data, indent=2), f"{timestamp}_{tool_name}_input_{call_id}.json")
    
    try:
        result = clarify_recipe_step(recipe, clarification_request)
        # Log success result to MLflow
        mlflow.log_metric(f"tool_success_{call_id}", 1)
        mlflow.log_text(json.dumps(result.dict(), indent=2), f"{timestamp}_{tool_name}_output_{call_id}.json")
        return result
    except ValidationError as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=CLARIFY_RECIPE_STEP_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response
    except OutputParserException as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=CLARIFY_RECIPE_STEP_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response

@tool
def web_search_tool(recipe: Recipe) -> Union[SearchResults, ErrorResponse]:
    """web_search_tool - searches the web for similar recipes using DuckDuckGo.

    Args:
        recipe (Recipe): The recipe to find similar alternatives for

    Returns:
        SearchResults: A list of similar recipes found online with their sources or an error message if validation fails
    """
    call_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tool_name = "web_search"
    
    # Prepare input data with prompt included
    input_data = {
        "recipe": recipe.dict(),
        "prompt_template": SEARCH_RECIPE_PROMPT
    }
    
    # Log tool call inputs to MLflow
    mlflow.log_param(f"tool_call_{call_id}", "web_search_tool")
    mlflow.log_text(json.dumps(input_data, indent=2), f"{timestamp}_{tool_name}_input_{call_id}.json")
    
    try:
        result = web_search(recipe)
        # Log success result to MLflow
        mlflow.log_metric(f"tool_success_{call_id}", 1)
        # Use the correct attribute from SearchResults (based on your Pydantic model)
        if hasattr(result, 'search_results'):
            mlflow.log_metric(f"search_results_count_{call_id}", len(result.search_results))
        mlflow.log_text(json.dumps(result.dict(), indent=2), f"{timestamp}_{tool_name}_output_{call_id}.json")
        return result
    except ValidationError as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=WEB_SEARCH_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response
    except OutputParserException as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=WEB_SEARCH_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response

@tool
def create_recipe_from_intent_tool(intent: str) -> Union[Recipe, ErrorResponse]:
    """create_recipe_from_intent_tool - creates a recipe from a natural language intent.
    
    Args:
        intent (str): Natural language description of the recipe the user wants to create
            (e.g., "make me a chocolate chip cookie recipe", "create a vegetarian pasta dish with spinach")
            
    Returns:
        Recipe: A complete recipe with title, ingredients, quantities, units, and steps or an error message if validation fails
    """
    call_id = str(uuid.uuid4())[:8]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tool_name = "create_recipe_from_intent"
    
    # Prepare input data with prompt included
    input_data = {
        "intent": intent,
        "prompt_template": CREATE_RECIPE_FROM_INTENT_PROMPT
    }
    
    # Log tool call inputs to MLflow
    mlflow.log_param(f"tool_call_{call_id}", "create_recipe_from_intent_tool")
    mlflow.log_text(json.dumps(input_data, indent=2), f"{timestamp}_{tool_name}_input_{call_id}.json")
    
    try:
        result = create_recipe_from_intent(intent)
        # Log success result to MLflow
        mlflow.log_metric(f"tool_success_{call_id}", 1)
        mlflow.log_text(json.dumps(result.dict(), indent=2), f"{timestamp}_{tool_name}_output_{call_id}.json")
        return result
    except ValidationError as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=CREATE_RECIPE_FROM_INTENT_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response
    except OutputParserException as e:
        # Log error to MLflow
        error_response = ErrorResponse(status="error", message=CREATE_RECIPE_FROM_INTENT_GUIDANCE)
        mlflow.log_metric(f"tool_error_{call_id}", 1)
        mlflow.log_text(str(e), f"{timestamp}_{tool_name}_error_{call_id}.txt")
        mlflow.log_text(json.dumps(error_response.dict(), indent=2), f"{timestamp}_{tool_name}_error_response_{call_id}.json")
        return error_response