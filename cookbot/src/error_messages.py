# cookbot/src/error_messages.py

ADJUST_QUANTITIES_GUIDANCE = (
    "Please ensure the adjustment description is clear and specific. "
    "For example, use phrases like 'double the recipe' or 'make it for 6 people instead of 4'. "
    "Check that the recipe object is complete with all necessary fields."
)

TRANSLATE_RECIPE_GUIDANCE = (
    "Please specify a valid target language for translation. "
    "Ensure the language code or name is correct and supported. "
    "Verify that the recipe object is properly structured."
)

CLARIFY_RECIPE_STEP_GUIDANCE = (
    "Please provide a specific clarification request. "
    "Mention the step number or description that needs clarification. "
    "Ensure the recipe object includes all necessary details."
)

WEB_SEARCH_GUIDANCE = (
    "Ensure the recipe object is complete and correctly formatted. "
    "Check that all required fields are present and valid. "
    "Consider simplifying the recipe details for better search results. Parse also the websites for the recipes."
)

CREATE_RECIPE_FROM_INTENT_GUIDANCE = (
    "Ensure the recipe object is complete and correctly formatted. "
    "Check that all required fields are present and valid. "
    "Consider simplifying the recipe details for better search results."
)