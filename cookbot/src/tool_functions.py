from src.chatmodel import ChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun
from src.pydantic_types import Recipe, ScalingFactor, SearchResults, TranslationOutput, ClarificationOutput
from src.prompts import TRANSLATE_RECIPE_PROMPT, ADJUST_RECIPE_QUANTITIES_PROMPT, CLARIFY_RECIPE_STEP_PROMPT, SEARCH_RECIPE_PROMPT, CREATE_RECIPE_FROM_INTENT_PROMPT


def translate_recipe(recipe: Recipe, language: str) -> TranslationOutput:
    """Translates a recipe's ingredients and steps into the specified language.

    Args:
        recipe (Recipe): The recipe to translate
        language (str): Target language for translation

    Returns:
        Translated ingredients and steps
    """

    structured_llm = ChatModel().model.with_structured_output(TranslationOutput, method="json_mode")
    prompt = ChatPromptTemplate.from_template(TRANSLATE_RECIPE_PROMPT)
    chain = prompt | structured_llm
    translated_recipe = chain.invoke({
        "language": language, 
        "recipe": recipe,
        "json_schema": TranslationOutput.model_json_schema()
    })
    
    return translated_recipe


def adjust_recipe_quantities(recipe: Recipe, quantity_adjustment_input: str) -> Recipe:
    """Adjusts the quantities of ingredients in a recipe based on a natural language input.
    
    Args:
        recipe (Recipe): The recipe object containing ingredients, quantities, units, and steps
        quantity_adjustment_input (str): Natural language description of how to adjust the recipe
            (e.g., "double the recipe", "make it for 6 people instead of 4", "half the portions")

    Returns:
        Recipe: A new Recipe object with adjusted quantities
    """
    prompt = ChatPromptTemplate.from_template(ADJUST_RECIPE_QUANTITIES_PROMPT)
    structured_llm = ChatModel().model.with_structured_output(ScalingFactor, method="json_mode")
    chain = prompt | structured_llm
    scaling_factor = chain.invoke({
        "recipe": recipe,
        "adjustment": quantity_adjustment_input,
        "json_schema": ScalingFactor.model_json_schema()
    })
    
    # Create a new Recipe object with adjusted quantities
    adjusted_quantities = [q * scaling_factor.multiplier for q in recipe.quantities]
    adjusted_recipe = Recipe(
        title=recipe.title,
        ingredients=recipe.ingredients,
        quantities=adjusted_quantities,
        units=recipe.units,
        steps=recipe.steps
    )
    
    return adjusted_recipe


def web_search(recipe: Recipe) -> SearchResults:
    """Searches the web for similar recipes using DuckDuckGo.

    Args:
        recipe (Recipe): The recipe to find similar alternatives for

    Returns:
        SearchResults: A list of similar recipes found online with their sources
    """
    search = DuckDuckGoSearchRun()
    # TODO: Web Search to Improve
    # Create a search query based on main ingredients and recipe type
    main_ingredients = ", ".join(recipe.ingredients[:3])  # Use first few ingredients
    search_query = f"recipe similar to {main_ingredients} {recipe.steps[0]}"
    
    # Perform the web search
    search_results = search.run(search_query)
    
    # Process the search results into a structured format
    prompt = ChatPromptTemplate.from_template(SEARCH_RECIPE_PROMPT)  # Missing prompt template
    
    structured_llm = ChatModel().model.with_structured_output(SearchResults, method="json_mode")
    chain = prompt | structured_llm
    
    parsed_results = chain.invoke({
        "ingredients": recipe.ingredients,
        "steps": recipe.steps,
        "search_results": search_results,
        "json_schema": SearchResults.model_json_schema()
    })
    
    return parsed_results

def clarify_recipe_step(recipe: Recipe, user_clarification_request: str) -> ClarificationOutput:
    """Analyzes a recipe and provides detailed clarifications for any steps that might be unclear or need additional explanation.

    Args:
        recipe (Recipe): A Recipe object containing ingredients, quantities, units, and preparation steps
        user_clarification_request (str): A user request for clarification of a specific step in the recipe

    Returns:
        ClarificationOutput: A detailed explanation of any steps that need clarification, including cooking techniques, 
    """
    clarification = ChatModel().model.invoke(CLARIFY_RECIPE_STEP_PROMPT.format(recipe=recipe, user_clarification_request=user_clarification_request))
    return ClarificationOutput(output=clarification.content)

def create_recipe_from_intent(intent: str) -> Recipe:
    """Creates a Recipe object from a natural language intent.

    Args:
        intent (str): A natural language description of the recipe to create

    Returns:
        Recipe: A Recipe object constructed from the intent
    """
    # Define a prompt template for creating a recipe from an intent
    prompt = ChatPromptTemplate.from_template(CREATE_RECIPE_FROM_INTENT_PROMPT)
    
    # Use the language model to parse the intent and generate a recipe
    structured_llm = ChatModel().model.with_structured_output(Recipe, method="json_mode")
    chain = prompt | structured_llm
    
    # Invoke the chain with the intent and the expected JSON schema for a Recipe
    recipe = chain.invoke({
        "intent": intent,
        "json_schema": Recipe.model_json_schema()
    })
    
    return recipe
