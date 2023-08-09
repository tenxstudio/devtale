import copy
import getpass
import json
import logging
import os

import click

from devtale.constants import ALLOWED_EXTENSIONS, LANGUAGES
from devtale.utils import (
    extract_code_elements,
    fuse_tales,
    get_tale_index,
    get_unit_tale,
    prepare_code_elements,
    redact_tale_information,
    split,
)

DEFAULT_OUTPUT_PATH = "devtale_demo/"
DEFAULT_MODEL_NAME = "gpt-4"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_repository(
    root_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
) -> None:
    folders = {}
    folder_tales = []
    for folder_path, _, filenames in os.walk(root_path):
        for filename in filenames:
            file_relative_path = os.path.relpath(
                os.path.join(folder_path, filename), root_path
            )
            folder_name, file_name = os.path.split(file_relative_path)
            # useful to keep a tree, we should use .gitignore to filter
            if folder_name not in folders:
                folders[folder_name] = [file_name]
            else:
                folders[folder_name].append(file_name)

    for folder_name in folders.keys():
        folder_path = os.path.join(root_path, folder_name)
        folder_tale = process_folder(folder_path, output_path)
        if folder_tale is not None:
            folder_tales.append(
                {"folder_name": folder_name, "folder_summary": folder_tale}
            )

    if folder_tales:
        root_index = get_tale_index(folder_tales)

        save_path = os.path.join(output_path, root_path)
        logger.info(f"saving root index in {save_path}")
        with open(os.path.join(save_path, "README.md"), "w", encoding="utf-8") as file:
            file.write(root_index)


def process_folder(
    folder_path: str,
    output_path: str,
    model_name: str = DEFAULT_MODEL_NAME,
) -> None:
    save_path = os.path.join(output_path, folder_path)
    tales = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if (
            os.path.isfile(file_path)
            and os.path.splitext(filename)[1] in ALLOWED_EXTENSIONS
        ):
            logger.info(f"processing {file_path}")
            file_tale = process_file(file_path, save_path)

            tales.append(
                {"file_name": filename, "file_summary": file_tale["file_docstring"]}
            )

    if tales:
        tales_index = get_tale_index(tales)
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        logger.info(f"saving index in {save_path}")
        with open(os.path.join(save_path, "README.md"), "w", encoding="utf-8") as file:
            file.write(tales_index)

        return tales_index
    return None


def process_file(
    file_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    logger.info("read dev draft")
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[-1]
    logger.info(f"extension: {file_ext}")

    with open(file_path, "r") as file:
        code = file.read()

    logger.info("split dev draft ideas")
    big_docs = split(code, language=LANGUAGES[file_ext], chunk_size=10000)
    short_docs = split(code, language=LANGUAGES[file_ext], chunk_size=3000)

    logger.info("extract code elements")
    code_elements = []
    for idx, doc in enumerate(big_docs):
        elements_set = extract_code_elements(doc)
        if elements_set:
            code_elements.append(elements_set)

    logger.info("prepare code elements")
    code_elements_dict = prepare_code_elements(code_elements)

    # Make a copy to keep the original dict intact
    code_elements_copy = copy.deepcopy(code_elements_dict)

    # clean
    code_elements_copy.pop("summary", None)
    if not code_elements_copy["classes"]:
        code_elements_copy.pop("classes", None)
    if not code_elements_copy["methods"]:
        code_elements_copy.pop("methods", None)

    logger.info("create tale sections")
    tales_list = []
    # process only if we have elements to document
    if code_elements_copy:
        for idx, doc in enumerate(short_docs):
            tale = get_unit_tale(doc, code_elements_copy, model_name=model_name)
            tales_list.append(tale)
            logger.info(f"tale section {str(idx+1)}/{len(short_docs)} done.")

    logger.info("write dev tale")
    tale = fuse_tales(tales_list, code, code_elements_dict)

    logger.info("add dev tale summary")
    tale["file_docstring"] = redact_tale_information("top-level", code_elements_dict)

    save_path = os.path.join(output_path, f"{file_name}.json")
    logger.info(f"save dev tale in: {save_path}")
    with open(save_path, "w") as json_file:
        json.dump(tale, json_file, indent=2)

    return tale


@click.command()
@click.option(
    "-p",
    "--path",
    "path",
    required=True,
    help="The path to the repository, folder, or file",
)
@click.option(
    "-r",
    "--recursive",
    "recursive",
    is_flag=True,
    default=False,
    help="Allows to explore subfolders.",
)
@click.option(
    "-o",
    "--output-path",
    "output_path",
    required=False,
    default=DEFAULT_OUTPUT_PATH,
    help="The destination folder where you want to save the documentation outputs",
)
@click.option(
    "-n",
    "--model-name",
    "model_name",
    required=False,
    default=DEFAULT_MODEL_NAME,
    help="The OpenAI model name you want to use. \
    https://platform.openai.com/docs/models",
)
def main(path: str, recursive: bool, output_path: str, model_name: str):
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass(
            prompt="Enter your OpenAI API key: "
        )

    if os.path.isdir(path):
        if recursive:
            logger.info("Processing repository")
            process_repository(path, output_path, model_name)
        else:
            logger.info("Processing folder")
            process_folder(path, output_path, model_name)
    elif os.path.isfile(path):
        logger.info("Processing file")
        process_file(path, output_path, model_name)
    else:
        raise f"Invalid input path {path}. Path must be a directory or code file."


if __name__ == "__main__":
    main()
