import json
import re
from json import JSONDecodeError

from langchain import LLMChain, PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter

from devtale.schema import FileDocumentation
from devtale.templates import (
    CODE_LEVEL_TEMPLATE,
    FILE_LEVEL_TEMPLATE,
    FOLDER_LEVEL_TEMPLATE,
)


def split(code, language, chunk_size=1000, chunk_overlap=0):
    code_splitter = RecursiveCharacterTextSplitter.from_language(
        language=language, chunk_size=chunk_size, chunk_overlap=0
    )
    docs = code_splitter.create_documents([code])
    return docs


def get_tale_index(tales, model_name="gpt-3.5-turbo", verbose=False):
    prompt = PromptTemplate(template=FOLDER_LEVEL_TEMPLATE, input_variables=["tales"])
    llm = ChatOpenAI(model_name=model_name)
    indixer = LLMChain(llm=llm, prompt=prompt, verbose=verbose)

    return indixer.run(str(tales))


def get_tale_summary(tale, model_name="gpt-3.5-turbo", verbose=False):
    prompt = PromptTemplate(template=FILE_LEVEL_TEMPLATE, input_variables=["tale"])
    llm = ChatOpenAI(model_name=model_name)
    summarizer = LLMChain(llm=llm, prompt=prompt, verbose=verbose)

    tale["file_docstring"] = summarizer.run(str(tale))
    return tale


def get_unit_tale(doc, model_name="gpt-3.5-turbo", verbose=False):
    parser = PydanticOutputParser(pydantic_object=FileDocumentation)
    prompt = PromptTemplate(
        template=CODE_LEVEL_TEMPLATE,
        input_variables=["code"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    teller_of_tales = LLMChain(
        llm=ChatOpenAI(model_name=model_name), prompt=prompt, verbose=verbose
    )
    result_string = teller_of_tales({"code": doc.page_content})
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
                print(f" something else {text}")
        except Exception as e:
            print(
                f"Error getting the JSON with the docstrings. \
                Error: {e} \n Result {json_text} \
                Error2: {result_json}"
            )
            print("Returning empty JSON instead")
            empty = {"classes": [], "methods": []}
            return empty
    return result_json


def is_hallucination(code_definition, code):
    # Check if the code_definition exists within the code
    if re.search(r"\b" + re.escape(code_definition) + r"\b", code):
        return False
    return True


def fuse_tales(tales_list, code):
    fused_tale = {"classes": [], "methods": []}
    unique_methods = set()
    unique_classes = set()

    for tale in tales_list:
        if "classes" in tale:
            for class_info in tale["classes"]:
                class_name = class_info["class_name"]
                if class_name not in unique_classes and not is_hallucination(
                    class_name, code
                ):
                    unique_classes.add(class_name)
                    fused_tale["classes"].append(class_info)

        if "methods" in tale:
            for method in tale["methods"]:
                method_name = method["method_name"]
                if method_name not in unique_methods and not is_hallucination(
                    method_name, code
                ):
                    unique_methods.add(method_name)
                    fused_tale["methods"].append(method)

    return fused_tale
