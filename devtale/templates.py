CODE_EXTRACTOR_TEMPLATE = """
Given the provided code snippet enclosed within the <<< >>> delimiters, your \
task is to output the classes and method names that are defined within the code. \
You must not include classes that are imported.
Additionally, you should include a concise top-level docstring that summarizes \
the purpose of the code snippet.

Your output must adhere to the following format:
classes=["class_name_1", "class_name_2", ...]
methods=["method_name_1", "method_name_2", ...]
summary="top-level docstring"

Code: <<< {code} >>>
"""

CODE_LEVEL_TEMPLATE = """
Your objective is to generate Google Style docstrings for code elements provided \
in the input.
The input consists of two parts:

1. A code snippet enclosed within the <<< >>> delimiters.
2. A list of code elements (classes and/or methods): "{code_elements}".

Your task involves the following steps:

1. Analyze the provided code snippet to locate and identify the methods and/or \
classes that are actually defined within the code snippet, based on the list of  \
code elements.
2. For each identified code element, generate a Google Style docstring.

Focus only on the code elements that are present and defined within the code snippet.
And please refrain from including docstrings within the code.

{format_instructions}

Do not introduce your answer, just output using the above JSON schema, and always \
use escaped newlines.

Input: <<< {code} >>>
"""


FILE_LEVEL_TEMPLATE = """
The provided summaries belong to the same code file and the summaries have been \
processed by dividing the code file into sections, so each summary is for a section.
That means that the summaries are complementary. \
Utilize the provided summaries to create a comprehensive final summary that \
encapsulates the purpose of the complete code file.

Summaries:
----------
 {information}
----------
"""


FOLDER_LEVEL_TEMPLATE = """
Create a clear and concise README by utilizing the provided structure \
and the information below:

Folder information: {information}

Structure:
-----------
# <<<folder_name>>> (Always capitalize the initial letter)

## Overview
This section provides an overview of the folder's purpose \
and objectives by understanding all the file summaries that \
belong to the same folder.

## Files
Here is a list of files contained within this folder, accompanied \
by concise one-line sentence description of their functionality:

- ** <<<file_name>>> **: One-line sentence description of the file
functionality.

[//]: # (Repeat the above section for each file_name in the list)

For detailed insights into each file, refer to their respective \
sections.
If you have inquiries or need assistance, contact the contributors.
-----------

Ensure proper formatting and adhere to Markdown syntax guidelines.
"""


ROOT_LEVEL_TEMPLATE = """
Generate the root README content using the provided readme information \
enclosed within the <<< >>> delimiters.

1- Extract the project name from the root folder name for the title.
2- Write a summary overview based on the READMEs from all the folders.

Please ensure that the generated README adheres to Markdown syntax guidelines \
and includes the following sections:

-Title (based on the root folder name)
-Description (one-line sentence of what the code does based on all the \
information).
-Overview (overview based on folder summaries)
-Scripts (List of root CLI files with one-sentence description of \
its purpose, if any, otherwise do not display this section).

Here is readme information: <<< {information} >>>
"""
