import json
import re
from json import JSONDecodeError

from langchain import LLMChain, OpenAI, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter

from devtale.schema import FileDocumentation
from devtale.templates import (
    CODE_EXTRACTOR_TEMPLATE,
    CODE_LEVEL_TEMPLATE,
    FILE_LEVEL_TEMPLATE,
    FOLDER_LEVEL_TEMPLATE,
    ROOT_LEVEL_TEMPLATE,
)

TYPE_INFORMATION = {
    "top-level": FILE_LEVEL_TEMPLATE,
    "folder-level": FOLDER_LEVEL_TEMPLATE,
    "root-level": ROOT_LEVEL_TEMPLATE,
}


def split(code, language, chunk_size=1000, chunk_overlap=0):
    code_splitter = RecursiveCharacterTextSplitter.from_language(
        language=language, chunk_size=chunk_size, chunk_overlap=0
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


def redact_tale_information(content_type, information, verbose=False):
    prompt = PromptTemplate(
        template=TYPE_INFORMATION[content_type], input_variables=["information"]
    )
    teller_of_tales = LLMChain(llm=OpenAI(), prompt=prompt, verbose=verbose)

    return teller_of_tales.run(str(information))


def get_tale_index(tales, model_name="gpt-3.5-turbo", verbose=False):
    prompt = PromptTemplate(template=FOLDER_LEVEL_TEMPLATE, input_variables=["tales"])
    llm = ChatOpenAI(model_name=model_name)
    indixer = LLMChain(llm=llm, prompt=prompt, verbose=verbose)

    return indixer.run(str(tales))


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
    try:
        result_json = json.loads(result_string["text"])
    except JSONDecodeError:
        try:
            text = result_string["text"].replace("\\n", "\n")
            start_index = text.find("{")
            end_index = text.rfind("}")

            if start_index != -1 and end_index != -1 and start_index < end_index:
                json_text = text[start_index : end_index + 1]
                result_json = json.loads(json_text)
            else:
                print(f"Ivalid JSON {text}")
                print("Returning empty JSON instead")
                empty = {"classes": [], "methods": []}
                return empty
        except Exception as e:
            print(
                f"Error getting the JSON with the docstrings. \
                Error: {e} \n Result: {result_string['text']}"
            )
            print("Returning empty JSON instead")
            empty = {"classes": [], "methods": []}
            return empty
    return result_json


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
    unique_methods = set()
    unique_classes = set()

    for tale in tales_list:
        if "classes" in tale:
            for class_info in tale["classes"]:
                class_name = class_info["class_name"]
                if class_name not in unique_classes and not is_hallucination(
                    class_name, code, code_elements_dict["classes"]
                ):
                    unique_classes.add(class_name)
                    fused_tale["classes"].append(class_info)

        if "methods" in tale:
            for method in tale["methods"]:
                method_name = method["method_name"]
                if method_name not in unique_methods and not is_hallucination(
                    method_name, code, code_elements_dict["methods"]
                ):
                    unique_methods.add(method_name)
                    fused_tale["methods"].append(method)

    return fused_tale
