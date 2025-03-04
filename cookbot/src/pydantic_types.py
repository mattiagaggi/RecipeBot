# We want the recipe to include everything, because also the clarifications need to be taken into account
from typing import List
from pydantic import BaseModel, Field
from typing import Union


class Recipe(BaseModel):
    ingredients: List[str] = Field(description="List of ingredient names.")
    quantities: List[Union[float, int]] = Field(description="List of quantities for each ingredient")
    units: List[str] = Field(description="List of units corresponding to each quantity")
    steps: List[str] = Field(description="Ordered list of recipe preparation steps")
    number_of_people: int = Field(description="Number of people the recipe is for")


class TranslationOutput(BaseModel):
    ingredients: List[str] = Field(description="List of ingredient names, make these as unambiguous as possible")
    steps: List[str] = Field(description="Ordered list of recipe preparation steps")


class ScalingFactor(BaseModel):
    # different recipes
    multiplier: float = Field(description="Factor I need to multiply the current quantities to adjust the recipe.")

class ClarificationOutput(BaseModel):
    output: str = Field(description="Clarification of the recipe step as a string")

class SearchResults(BaseModel):
    recipes: List[str] = Field(description="List of recipe names and brief descriptions found through search")
    sources: List[str] = Field(description="List of URLs where these recipes were found")

class ErrorResponse(BaseModel):
    status: str
    message: str