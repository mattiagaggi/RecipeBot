import pytest
from src.tool_functions import translate_recipe, adjust_recipe_quantities, web_search, clarify_recipe_step, create_recipe_from_intent
from src.pydantic_types import Recipe, TranslationOutput, SearchResults, ClarificationOutput
import unittest

@pytest.fixture
def sample_recipe():
    return Recipe(
        ingredients=["chicken breast", "olive oil", "garlic"],
        quantities=[2, 2, 3],
        units=["pieces", "tablespoons", "cloves"],
        steps=["Season chicken with salt and pepper", "Heat oil in pan", "Cook chicken until golden"],
        number_of_people=4
    )

def test_translate_recipe_correct_output(sample_recipe):
    result = translate_recipe(sample_recipe, "Spanish")
    
    assert isinstance(result, TranslationOutput)
    assert isinstance(result.ingredients, list)  # Ensure ingredients is a list
    assert len(result.ingredients) == len(sample_recipe.ingredients)
    assert len(result.steps) == len(sample_recipe.steps)
    assert all(isinstance(ingredient, str) for ingredient in result.ingredients)
    assert all(isinstance(step, str) for step in result.steps)

def test_adjust_recipe_quantities_correct_output(sample_recipe):
    result = adjust_recipe_quantities(sample_recipe, "double the recipe")
    
    assert isinstance(result, list)
    assert len(result) == len(sample_recipe.quantities)
    assert all(isinstance(q, (int, float)) for q in result)
    # Test doubling
    assert result == [q * 2 for q in sample_recipe.quantities]

def test_web_search_correct_output(sample_recipe):
    result = web_search(sample_recipe)
    
    assert isinstance(result, SearchResults)
    assert hasattr(result, 'recipes')
    assert hasattr(result, 'sources')
    assert len(result.recipes) > 0
    assert len(result.sources) > 0
    assert all(isinstance(recipe, str) for recipe in result.recipes)
    assert all(isinstance(source, str) for source in result.sources)

def test_clarify_recipe_step_correct_output(sample_recipe):
    clarification_request = "How do I know when the chicken is done?"
    result = clarify_recipe_step(sample_recipe, clarification_request)
    
    assert isinstance(result, ClarificationOutput)
    assert len(result.output) > 0
    # Check that the response contains relevant cooking terms/concepts
    assert any(term in result.output.lower() for term in ['temperature', 'internal', 'cooked', 'safe', 'done'])

def test_create_recipe_from_intent():
    """Test creating a recipe from a natural language intent."""
    # Arrange
    intent = "I want to make a chocolate cake with a rich chocolate flavor and a moist texture."

    # Act
    recipe = create_recipe_from_intent(intent)

    # Assert
    assert isinstance(recipe, Recipe), "The result should be an instance of Recipe."
    assert isinstance(recipe.ingredients, list), "Ingredients should be a list."
    assert hasattr(recipe, 'ingredients'), "Recipe should have 'ingredients' attribute."
    assert hasattr(recipe, 'steps'), "Recipe should have 'steps' attribute."
    assert len(recipe.ingredients) > 0, "Ingredients should not be empty."
    assert len(recipe.steps) > 0, "Steps should not be empty."

if __name__ == '__main__':
    unittest.main()




