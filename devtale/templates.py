CODE_LEVEL_TEMPLATE = """
Given the provided code text input enclosed within the <<< >>> delimiters, your \
task is to create well-structured documentation for the classes, methods, and  \
functions explicitly defined within the code.
You are not allowed to generate new classes, methods or functions.
Skip class instances, imported classes, imported methods, method instances.
Output your answer as a JSON which matches the following output format.

Ouput format: {format_instructions}

Input: <<< {code} >>>
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


FOLDER_LEVEL_TEMPLATE = """
Use the following information delimeted by <<< >>> to write a README file:

Start with a descriptive title that clearly indicates the folder's purpose. Follow it \
up with a brief description that provides an overview of what the folder contains and \
its intended use.

Provide explanations for each significant file within the folder. The explanations \
should be one-sentence long.

Add any other relevant information that could be helpful for users or contributors \

Remember that the README should be written in a clear and concise manner, using \
appropriate formatting, and follow Markdown syntax

<<< {tales} >>>
"""
