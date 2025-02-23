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
    try:
        return adjust_recipe_quantities(recipe, adjustment)
    except ValidationError:
        return ErrorResponse(status="error", message=ADJUST_QUANTITIES_GUIDANCE)
    except OutputParserException:
        return ErrorResponse(status="error", message=ADJUST_QUANTITIES_GUIDANCE)

@tool
def translate_recipe_tool(recipe: Recipe, language: str) -> Union[TranslationOutput, ErrorResponse]:
    """translate_recipe_tool-translates a recipe's ingredients and steps into the specified language.

    Args:
        recipe (Recipe): The recipe to translate
        language (str): Target language for translation

    Returns:
        Translated ingredients and steps as a list of strings or an error message if validation fails
    """
    try:
        return translate_recipe(recipe, language)
    except ValidationError:
        return ErrorResponse(status="error", message=TRANSLATE_RECIPE_GUIDANCE)
    except OutputParserException:
        return ErrorResponse(status="error", message=TRANSLATE_RECIPE_GUIDANCE)

@tool
def clarify_recipe_step_tool(recipe: Recipe, clarification_request: str) -> Union[ClarificationOutput, ErrorResponse]:
    """clarify_recipe_step_tool - analyzes a recipe and provides detailed clarifications for any steps that might be unclear or need additional explanation.

    Args:
        recipe (Recipe): A Recipe object containing ingredients, quantities, units, and preparation steps
        user_clarification_request (str): A user request for clarification of a specific step in the recipe

    Returns:
        ClarificationOutput: A detailed explanation of any steps that need clarification, including cooking techniques, 
    """
    try:
        return clarify_recipe_step(recipe, clarification_request)
    except ValidationError:
        return ErrorResponse(status="error", message=CLARIFY_RECIPE_STEP_GUIDANCE)
    except OutputParserException:
        return ErrorResponse(status="error", message=CLARIFY_RECIPE_STEP_GUIDANCE)

@tool
def web_search_tool(recipe: Recipe) -> Union[SearchResults, ErrorResponse]:
    """web_search_tool - searches the web for similar recipes using DuckDuckGo.

    Args:
        recipe (Recipe): The recipe to find similar alternatives for

    Returns:
        SearchResults: A list of similar recipes found online with their sources or an error message if validation fails
    """
    try:
        return web_search(recipe)
    except ValidationError:
        return ErrorResponse(status="error", message=WEB_SEARCH_GUIDANCE)
    except OutputParserException:
        return ErrorResponse(status="error", message=WEB_SEARCH_GUIDANCE)

@tool
def create_recipe_from_intent_tool(intent: str) -> Union[Recipe, ErrorResponse]:
    """create_recipe_from_intent_tool - creates a recipe from a natural language intent."""
    try:
        return create_recipe_from_intent(intent)
    except ValidationError:
        return ErrorResponse(status="error", message=CREATE_RECIPE_FROM_INTENT_GUIDANCE)
    except OutputParserException:
        return ErrorResponse(status="error", message=CREATE_RECIPE_FROM_INTENT_GUIDANCE)