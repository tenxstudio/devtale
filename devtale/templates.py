CODE_LEVEL_TEMPLATE = """
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

FILE_LEVEL_TEMPLATE = """
Using the provided code file info, which contains descriptions of the file classes and \
methods. Please write a file-level summary/overview that can be added at the top level \
of the file to briefly explain what this file if for.

The summary should be understandable for non-programmers.
Do not re-explain what classes and functions it have and what they do.

Code File Info:
----------
 {tale}
----------
"""
