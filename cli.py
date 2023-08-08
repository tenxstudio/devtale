import getpass
import json
import logging
import os

import click

from devtale.constants import ALLOWED_EXTENSIONS, LANGUAGES
from devtale.utils import (
    fuse_tales,
    get_tale_index,
    get_tale_summary,
    get_unit_tale,
    split,
)

DEFAULT_OUTPUT_PATH = "devtale_demo/"
DEFAULT_MODEL_NAME = "gpt-3.5-turbo"


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
    docs = split(code, language=LANGUAGES[file_ext], chunk_size=3000)

    logger.info("create tale sections")
    tales_list = []
    for idx, doc in enumerate(docs):
        tale = get_unit_tale(doc, model_name=model_name)
        tales_list.append(tale)
        logger.info(f"tale section {str(idx+1)}/{len(docs)} done.")

    logger.info("write dev tale")
    file_tales = fuse_tales(tales_list, code)

    logger.info("add dev tale summary")
    final_tale = get_tale_summary(file_tales)

    save_path = os.path.join(output_path, f"{file_name}.json")
    logger.info(f"save dev tale in: {save_path}")
    with open(save_path, "w") as json_file:
        json.dump(final_tale, json_file, indent=2)

    return final_tale

    # logger.info("add documentation to the code")
    # documented_code = add_tales(file_tales, code)

    # save_path = os.path.join(output_path, file_name)
    # logger.info(f"save documented file in {save_path}")
    # with open(save_path, "w") as file:
    #    file.write(documented_code)


@click.command()
@click.option(
    "-m",
    "--mode",
    type=click.Choice(["-r", "-d", "-f"]),
    required=True,
    help="Select the mode: -r for repository, -d for folder, -f for file",
)
@click.option(
    "-p",
    "--path",
    "path",
    required=True,
    help="The path to the repository, folder, or file",
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
def main(mode: str, path: str, output_path: str, model_name: str):
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass(
            prompt="Enter your OpenAI API key: "
        )

    if mode == "-r":
        process_repository(path, output_path, model_name)
    elif mode == "-d":
        process_folder(path, output_path, model_name)
    elif mode == "-f":
        process_file(path, output_path, model_name)
    else:
        raise "Invalid mode. Please select -r (repository), -d (folder), or -f (file)."


if __name__ == "__main__":
    main()
