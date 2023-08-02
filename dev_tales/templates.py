FILE_LEVEL_TEMPLATE = """
Given the provided code, please perform the following actions:

1. Split the code into class definitions and method definitions.
2. For each class definition, generate a Google Style Docstring that provides an \
explanation of the purpose of the class.
3. For each method definition, generate a Google Style Docstring that provides an \
explanation of the purpose of the method.
4. If there is no file-level docstring already present in the code, generate a \
code multi-line comment to provide
an overview or summary of the purpose of the entire code.

{format_instructions}

Here is the code:
--------
{code}
--------
"""
