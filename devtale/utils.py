import json
import os
import re
from json import JSONDecodeError
from pathlib import Path

import json_repair
import tiktoken
from langchain import LLMChain, PromptTemplate
from langchain.callbacks import get_openai_callback
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter

from devtale.aggregators import (
    GoAggregator,
    JavascriptAggregator,
    PHPAggregator,
    PythonAggregator,
)
from devtale.constants import DOCSTRING_LABEL, GPT_PRICE
from devtale.schema import FileDocumentation
from devtale.templates import (
    CODE_EXTRACTOR_TEMPLATE,
    CODE_LEVEL_TEMPLATE,
    FILE_LEVEL_TEMPLATE,
    FOLDER_LEVEL_TEMPLATE,
    FOLDER_SHORT_DESCRIPTION_TEMPLATE,
    NO_CODE_FILE_TEMPLATE,
    ROOT_LEVEL_TEMPLATE,
)

TYPE_INFORMATION = {
    "top-level": FILE_LEVEL_TEMPLATE,
    "folder-level": FOLDER_LEVEL_TEMPLATE,
    "root-level": ROOT_LEVEL_TEMPLATE,
    "no-code-file": NO_CODE_FILE_TEMPLATE,
    "folder-description": FOLDER_SHORT_DESCRIPTION_TEMPLATE,
}


def split_text(text, chunk_size=1000, chunk_overlap=0):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    docs = text_splitter.create_documents([text])
    return docs


def split_code(code, language, chunk_size=1000, chunk_overlap=0):
    code_splitter = RecursiveCharacterTextSplitter.from_language(
        language=language, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    docs = code_splitter.create_documents([code])
    return docs


def extract_code_elements(
    big_doc, verbose=False, model_name="gpt-4-1106-preview", cost_estimation=False
):
    prompt = PromptTemplate(
        template=CODE_EXTRACTOR_TEMPLATE,
        input_variables=["code"],
    )
    extractor = LLMChain(
        llm=ChatOpenAI(model_name=model_name), prompt=prompt, verbose=verbose
    )

    if cost_estimation:
        estimated_cost = _calculate_cost(
            prompt.format(code=big_doc.page_content), model_name
        )
        return "", estimated_cost

    with get_openai_callback() as cb:
        result_string = extractor({"code": big_doc.page_content})
        cost = cb.total_cost

    return result_string["text"], cost


def get_unit_tale(
    short_doc,
    code_elements,
    model_name="gpt-4-1106-preview",
    verbose=False,
    cost_estimation=False,
):
    parser = PydanticOutputParser(pydantic_object=FileDocumentation)
    prompt = PromptTemplate(
        template=CODE_LEVEL_TEMPLATE,
        input_variables=["code", "code_elements"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    teller_of_tales = LLMChain(
        llm=ChatOpenAI(model_name=model_name), prompt=prompt, verbose=verbose
    )

    if cost_estimation:
        estimated_cost = _calculate_cost(
            prompt.format(
                code=short_doc.page_content, code_elements=str(code_elements)
            ),
            model_name,
        )
        return {"classes": [], "methods": []}, estimated_cost

    with get_openai_callback() as cb:
        result_string = teller_of_tales(
            {"code": short_doc.page_content, "code_elements": code_elements}
        )
        cost = cb.total_cost

    json_answer = _convert_to_json(result_string)
    if not json_answer:
        print("Returning empty JSON due to a failure")
        json_answer = {"classes": [], "methods": []}
    return json_answer, cost


def redact_tale_information(
    content_type,
    docs,
    verbose=False,
    model_name="gpt-3.5-turbo",
    cost_estimation=False,
):
    prompt = PromptTemplate(
        template=TYPE_INFORMATION[content_type], input_variables=["information"]
    )
    teller_of_tales = LLMChain(
        llm=ChatOpenAI(model_name=model_name), prompt=prompt, verbose=verbose
    )
    if content_type not in ["no-code-file", "folder-description"]:
        information = str(docs[0].page_content)
    else:
        information = str(docs)

    if cost_estimation:
        estimated_cost = _calculate_cost(
            prompt.format(information=information), model_name
        )
        return "", estimated_cost

    with get_openai_callback() as cb:
        text_answer = teller_of_tales({"information": information})
        cost = cb.total_cost

    return text_answer["text"], cost


def prepare_code_elements(code_elements):
    """Convert GPT text output into a dictionary and combine each
    dictionary into a single, general one
    """
    elements = {"classes": [], "methods": [], "summary": []}
    for code_element in code_elements:
        info = _process_extracted_code_element(code_element)
        elements["classes"].extend(info["classes"])
        elements["methods"].extend(info["methods"])
        elements["summary"].append(info["summary"])

    # remove duplicates
    elements["classes"] = list(set(elements["classes"]))
    elements["methods"] = list(set(elements["methods"]))
    return elements


def fuse_tales_chunks(tales_list, code, code_elements_dict):
    """Combine all the generated docstrings JSON-formatted GPT outputs into
    a single one, remove hallucinations and duplicates.
    """
    fused_tale = {"classes": [], "methods": []}
    errors = []
    unique_methods = set()
    unique_classes = set()

    for tale in tales_list:
        if "classes" in tale:
            for class_info in tale["classes"]:
                if isinstance(class_info, dict):
                    class_name = class_info["class_name"]
                    if class_name not in unique_classes and not _is_hallucination(
                        class_name, code, code_elements_dict["classes"]
                    ):
                        unique_classes.add(class_name)
                        # Attach the devtale label on each docstring
                        class_info["class_docstring"] = (
                            DOCSTRING_LABEL + "\n" + class_info["class_docstring"]
                        )
                        fused_tale["classes"].append(class_info)
                else:
                    if tale not in errors:
                        errors.append(tale)

        if "methods" in tale:
            for method_info in tale["methods"]:
                if isinstance(method_info, dict):
                    method_name = method_info["method_name"]
                    if method_name not in unique_methods and not _is_hallucination(
                        method_name, code, code_elements_dict["methods"]
                    ):
                        unique_methods.add(method_name)
                        # Attach the dectale label on each docstring
                        method_info["method_docstring"] = (
                            DOCSTRING_LABEL + "\n" + method_info["method_docstring"]
                        )
                        fused_tale["methods"].append(method_info)
                else:
                    if tale not in errors:
                        errors.append(tale)

    return fused_tale, errors


def build_project_tree(root_dir, indent="", gitignore_patterns=None):
    if gitignore_patterns is None:
        gitignore_patterns = []

    tree = ""
    items = [item for item in os.listdir(root_dir) if not item.startswith(".")]
    file_paths = []

    for item in sorted(items):
        item_path = os.path.join(root_dir, item)
        if _should_ignore(item_path, gitignore_patterns):
            continue
        if os.path.isdir(item_path):
            tree += indent + "├── " + item + "\n"
            subtree, subfile_paths = build_project_tree(
                item_path, indent + "│   ", gitignore_patterns
            )
            tree += subtree
            file_paths.extend(subfile_paths)
        else:
            tree += indent + "└── " + item + "\n"
            file_paths.append(item_path)

    return tree, file_paths


def fuse_documentation(code, tale, file_ext, save_path):
    if file_ext == ".py":
        aggregator = PythonAggregator()
    elif file_ext == ".php":
        aggregator = PHPAggregator()
    elif file_ext == ".go":
        aggregator = GoAggregator()
    elif file_ext == ".js" or file_ext == ".ts" or file_ext == ".tsx":
        aggregator = JavascriptAggregator()

    fused_tale = aggregator.document(code=code, documentation=tale)
    with open(save_path, "w") as file:
        file.write(fused_tale)


def _calculate_cost(input: str, model: str):
    tokens = tiktoken.get_encoding("cl100k_base").encode(input)
    return (len(tokens) / 1000) * GPT_PRICE[model]


def _convert_to_json(text_answer):
    try:
        result_json = json.loads(text_answer["text"])
        return result_json
    except JSONDecodeError:
        try:
            text = text_answer["text"].replace("\\n", "\n")
            start_index = text.find("{")
            end_index = text.rfind("}")

            if start_index != -1 and end_index != -1 and start_index < end_index:
                json_text = text[start_index : end_index + 1]

            result_json = json_repair.loads(json_text)
            return result_json

        except Exception as e:
            print(
                f"Error getting the JSON. \
                Error: {e} \n Result: {text_answer['text']}"
            )
            return None


def _add_escape_characters(invalid_json):
    control_char_pattern = re.compile(r"[\x00-\x1F\x7F-\x9F]")
    unescaped_chars = control_char_pattern.findall(invalid_json)

    # Escape the unescaped control characters
    for char in unescaped_chars:
        invalid_json = invalid_json.replace(char, "\\u{:04x}".format(ord(char)))

    return invalid_json


def _process_extracted_code_element(text: str):
    """It converts GPT text output into a dictionary of code elements"""
    classes_match = re.search(r"classes=(\[.*?\])", text)
    methods_match = re.search(r"methods=(\[.*?\])", text)
    summary_match = re.search(r'summary="([^"]*)"', text)

    classes = []
    methods = []
    summary = ""

    if classes_match:
        classes_str = classes_match.group(1)
        classes = re.findall(r'"(.*?)"', classes_str)

    if methods_match:
        methods_str = methods_match.group(1)
        methods = re.findall(r'"(.*?)"', methods_str)

    if summary_match:
        summary = summary_match.group(1)

    return {"classes": classes, "methods": methods, "summary": summary}


def _is_hallucination(code_definition, code, expected_definitions):
    # Verify that the code_definition is expected
    if code_definition not in expected_definitions:
        return True

    # Check if the code_definition exists within the code
    if not re.search(r"\b" + re.escape(code_definition) + r"\b", code):
        return True
    return False


def _should_ignore(path, gitignore_patterns):
    path = Path(path)
    for pattern in gitignore_patterns:
        if path.match(pattern) or any(p.match(pattern) for p in path.parents):
            return True
    return False
