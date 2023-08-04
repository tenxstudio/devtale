FILE_LEVEL_TEMPLATE = """
Given the provided code, please perform the following actions:

1. Split the code into class definitions and method definitions.
2. For each class definition, generate a Google Style Docstring text that provides an \
explanation of the purpose of the class, args and returns.
3. For each method definition, generate a Google Style Docstring text that provides an \
explanation of the purpose of the method, args, returns, and raises.

{format_instructions}

Here is the code:
--------
{code}
--------
"""
