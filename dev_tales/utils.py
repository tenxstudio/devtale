import json
import re

from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.text_splitter import Language, RecursiveCharacterTextSplitter

from dev_tales.schema import FileDocumentation
from dev_tales.templates import FILE_LEVEL_TEMPLATE

identifiers = {"php": ["class", "function"]}


def split(code, language=Language.PHP, chunk_size=1000, chunk_overlap=0):
    code_splitter = RecursiveCharacterTextSplitter.from_language(
        language=language, chunk_size=chunk_size, chunk_overlap=0
    )
    docs = code_splitter.create_documents([code])
    return docs


def get_unit_tale(doc, model_name="gpt-3.5-turbo", verbose=False):
    parser = PydanticOutputParser(pydantic_object=FileDocumentation)
    prompt = PromptTemplate(
        template=FILE_LEVEL_TEMPLATE,
        input_variables=["code"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    teller_of_tales = LLMChain(
        llm=ChatOpenAI(model_name=model_name), prompt=prompt, verbose=verbose
    )
    result_string = teller_of_tales({"code": doc.page_content})
    try:
        result_json = json.loads(result_string["text"])
    except Exception as e:
        print(
            f"Error getting the JSON with the docstrings. \
            Error: {e} \n Result {result_string}"
        )
        print("Returning empty JSON instead")
        empty = {"file_docstring": "", "classes": [], "methods": []}
        return empty
    return result_json


def add_tales(docstrings, code, language="php", signature="@AI-generated docstring"):
    documented_code = code
    class_identifier = identifiers[language][0]
    method_identifier = identifiers[language][1]

    # write class-level docstrings
    for class_info in docstrings["classes"]:
        class_name = class_info["class_name"]
        class_docstring = class_info["class_docstring"]
        documented_code = re.sub(
            r"(" + class_identifier + "\s+" + re.escape(class_name) + r"\s*\{)",
            r"/** " + signature + "\n * " + class_docstring + r"\n */\n\1",
            documented_code,
            count=1,
        )

    # write method-level docstrings
    for method_info in docstrings["methods"]:
        method_name = method_info["method_name"]
        method_docstring = method_info["method_docstring"]
        documented_code = re.sub(
            r"(" + method_identifier + "\s+" + re.escape(method_name) + r"\s*\()",
            r"\n/** " + signature + "\n * " + method_docstring + r"\n */\n\1",
            documented_code,
        )

    # write file-level docstring
    f"/*\n * {docstrings['file_docstring']}\n */\n{documented_code}"

    return documented_code


def fuse_tales(tales_list):
    fused_tale = {"file_docstring": "", "classes": [], "methods": []}
    for tale in tales_list:
        if "file_docstring" in tale:
            fused_tale["file_docstring"] += tale["file_docstring"] + "\n"
        if "classes" in tale:
            fused_tale["classes"].extend(tale["classes"])
        if "methods" in tale:
            fused_tale["methods"].extend(tale["methods"])

    return fused_tale
