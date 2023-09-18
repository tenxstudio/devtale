import json
import os
import re
from json import JSONDecodeError
from pathlib import Path

from langchain import LLMChain, OpenAI, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter

from devtale.constants import DOCSTRING_LABEL
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


def extract_code_elements(big_doc, verbose=False):
    prompt = PromptTemplate(
        template=CODE_EXTRACTOR_TEMPLATE,
        input_variables=["code"],
    )
    extractor = LLMChain(
        llm=ChatOpenAI(model_name="gpt-4"), prompt=prompt, verbose=verbose
    )

    result_string = extractor({"code": big_doc.page_content})
    return result_string["text"]


def _process_extracted_code_element(text: str):
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


def prepare_code_elements(code_elements):
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


def redact_tale_information(
    content_type, docs, verbose=False, model_name="text-davinci-003"
):
    prompt = PromptTemplate(
        template=TYPE_INFORMATION[content_type], input_variables=["information"]
    )
    teller_of_tales = LLMChain(
        llm=OpenAI(model_name=model_name), prompt=prompt, verbose=verbose
    )
    if content_type not in ["no-code-file", "folder-description"]:
        information = str(docs[0].page_content)
    else:
        information = str(docs)

    text_answer = teller_of_tales({"information": information})

    return text_answer


def convert_to_json(text_answer):
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

            json_text = _add_escape_characters(json_text)
            result_json = json.loads(json_text)
            return result_json

        except Exception as e:
            print(
                f"Error getting the JSON. \
                Error: {e} \n Result: {text_answer['text']}"
            )
            return None


def get_unit_tale(short_doc, code_elements, model_name="gpt-4", verbose=False):
    parser = PydanticOutputParser(pydantic_object=FileDocumentation)
    prompt = PromptTemplate(
        template=CODE_LEVEL_TEMPLATE,
        input_variables=["code", "code_elements"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    teller_of_tales = LLMChain(
        llm=ChatOpenAI(model_name=model_name), prompt=prompt, verbose=verbose
    )

    result_string = teller_of_tales(
        {"code": short_doc.page_content, "code_elements": code_elements}
    )
    json_answer = convert_to_json(result_string)
    if not json_answer:
        print("Returning empty JSON due to a failure")
        json_answer = {"classes": [], "methods": []}
    return json_answer


def is_hallucination(code_definition, code, expected_definitions):
    # Verify that the code_definition is expected
    if code_definition not in expected_definitions:
        return True

    # Check if the code_definition exists within the code
    if not re.search(r"\b" + re.escape(code_definition) + r"\b", code):
        return True
    return False


def fuse_tales(tales_list, code, code_elements_dict):
    fused_tale = {"classes": [], "methods": []}
    errors = []
    unique_methods = set()
    unique_classes = set()

    for tale in tales_list:
        if "classes" in tale:
            for class_info in tale["classes"]:
                if isinstance(class_info, dict):
                    class_name = class_info["class_name"]
                    if class_name not in unique_classes and not is_hallucination(
                        class_name, code, code_elements_dict["classes"]
                    ):
                        unique_classes.add(class_name)
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
                    if method_name not in unique_methods and not is_hallucination(
                        method_name, code, code_elements_dict["methods"]
                    ):
                        unique_methods.add(method_name)
                        method_info["method_docstring"] = (
                            DOCSTRING_LABEL + "\n" + method_info["method_docstring"]
                        )
                        fused_tale["methods"].append(method_info)
                else:
                    if tale not in errors:
                        errors.append(tale)

    return fused_tale, errors


def _add_escape_characters(invalid_json):
    control_char_pattern = re.compile(r"[\x00-\x1F\x7F-\x9F]")
    unescaped_chars = control_char_pattern.findall(invalid_json)

    # Escape the unescaped control characters
    for char in unescaped_chars:
        invalid_json = invalid_json.replace(char, "\\u{:04x}".format(ord(char)))

    return invalid_json


def _should_ignore(path, gitignore_patterns):
    path = Path(path)
    for pattern in gitignore_patterns:
        if path.match(pattern) or any(p.match(pattern) for p in path.parents):
            return True
    return False


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
