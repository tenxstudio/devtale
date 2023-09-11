import copy
import getpass
import json
import logging
import os

import click
from dotenv import load_dotenv

from devtale.aggregators import GoAggregator, PHPAggregator, PythonAggregator
from devtale.constants import ALLOWED_EXTENSIONS, LANGUAGES
from devtale.utils import (
    build_project_tree,
    extract_code_elements,
    fuse_tales,
    get_unit_tale,
    prepare_code_elements,
    redact_tale_information,
    split_code,
    split_text,
)

DEFAULT_OUTPUT_PATH = "devtale_demo/"
DEFAULT_MODEL_NAME = "gpt-4"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_repository(
    root_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    fuse: bool = False,
) -> None:
    folder_tales = {
        "repository_name": os.path.basename(os.path.abspath(root_path)),
        "folders": [],
    }

    # get project structure before we modify it
    gitignore_path = os.path.join(root_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as gitignore_file:
            gitignore_patterns = [
                line.strip() for line in gitignore_file if line.strip()
            ]
    else:
        gitignore_patterns = None

    project_tree, file_paths = build_project_tree(
        root_path, gitignore_patterns=gitignore_patterns
    )
    project_tree = ".\n" + project_tree

    folders = list(set([os.path.dirname(file_path) for file_path in file_paths]))
    folders_readmes = []

    for folder_path in folders:
        try:
            if folder_path == root_path:
                folder_path += "/"
            folder_readme, folder_tale = process_folder(
                folder_path, output_path, model_name, fuse
            )
        except Exception as e:
            folder_name = os.path.basename(folder_path)
            logger.info(
                f"Failed to create folder-level tale for {folder_name} - Exception: {e}"
            )
            folder_tale = None

        if folder_tale is not None:
            # add root folder summary information
            if (
                os.path.basename(folder_path) == os.path.basename(root_path + "/")
                or os.path.basename(folder_path) == ""
            ):
                folder_tales["folders"].append(
                    {
                        "folder_name": os.path.basename(os.path.abspath(root_path)),
                        "folder_summary": folder_tale,
                        "is_the_root_folder": True,
                    }
                )
            else:
                folders_readmes.append(folder_readme)
                folder_tales["folders"].append(
                    {
                        "folder_name": os.path.basename(folder_path),
                        "folder_summary": folder_tale,
                    }
                )

    if folder_tales:
        folder_summaries = split_text(str(folder_tales), chunk_size=15000)
        root_readme = redact_tale_information(
            "root-level", folder_summaries, model_name="gpt-3.5-turbo-16k"
        )["text"]
        root_readme = root_readme.replace("----------", "")

        # inject folders information
        if folders_readmes:
            folders_information = "\n\n## Folders\n\n" + "".join(folders_readmes)
            root_readme = root_readme + folders_information

        # inject project tree
        tree = f"\n\n## Project Tree\n```bash\n{project_tree}```\n\n"
        root_readme = root_readme + tree

        logger.info("save root json..")
        with open(os.path.join(output_path, "root_level.json"), "w") as json_file:
            json.dump(folder_tales, json_file, indent=2)

        logger.info(f"saving root index in {output_path}")
        with open(
            os.path.join(output_path, "README.md"), "w", encoding="utf-8"
        ) as file:
            file.write(root_readme)


def process_folder(
    folder_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    fuse: bool = False,
) -> None:
    save_path = os.path.join(output_path, os.path.basename(folder_path))
    tales = []

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if (
            os.path.isfile(file_path)
            and os.path.splitext(file_name)[1] in ALLOWED_EXTENSIONS
        ):
            logger.info(f"processing {file_path}")
            try:
                file_tale = process_file(file_path, save_path, model_name, fuse)
            except Exception as e:
                logger.info(
                    f"Failed to create dev tale for {file_path} - Exception: {e}"
                )
                file_tale = None

            if file_tale is not None:
                if file_tale["file_docstring"]:
                    folder_name = os.path.basename(os.path.abspath(folder_path))
                    folder_entry = next(
                        (item for item in tales if item["folder_name"] == folder_name),
                        None,
                    )
                    if folder_entry is None:
                        folder_entry = {
                            "folder_name": folder_name,
                            "folder_files": [],
                        }
                        tales.append(folder_entry)

                    folder_entry["folder_files"].append(
                        {
                            "file_name": file_name,
                            "file_description": file_tale["file_docstring"],
                        }
                    )

    if tales:
        files_summaries = split_text(str(tales), chunk_size=10000)
        folder_info = redact_tale_information(
            "folder-level", files_summaries, model_name="gpt-3.5-turbo-16k"
        )

        folder_readme = folder_info["folder_readme"].replace("----------", "")
        folder_tale = folder_info["folder_overview"]

        logger.info("save folder json..")
        with open(os.path.join(save_path, "folder_level.json"), "w") as json_file:
            json.dump(tales, json_file, indent=2)

        logger.info(f"saving index in {save_path}")
        with open(os.path.join(save_path, "README.md"), "w", encoding="utf-8") as file:
            file.write(folder_readme)

        return folder_readme, folder_tale
    return None


def process_file(
    file_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    fuse: bool = False,
) -> None:
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[-1]
    save_path = os.path.join(output_path, f"{file_name}.json")

    logger.info("read dev draft")
    with open(file_path, "r") as file:
        code = file.read()

    if not code:
        return {"file_docstring": ""}

    if os.path.exists(save_path):
        logger.info(f"Skipping {file_name} as its tale file already exists.")
        with open(save_path, "r") as file:
            found_tale = json.load(file)
        if fuse:
            fuse_documentation(code, found_tale, output_path, file_name, file_ext)
        return found_tale

    if not file_ext:
        bash_docstring = redact_tale_information("unknow-top-level", code)["text"]
        return {"file_docstring": bash_docstring}

    logger.info("split dev draft ideas")
    big_docs = split_code(code, language=LANGUAGES[file_ext], chunk_size=10000)
    short_docs = split_code(code, language=LANGUAGES[file_ext], chunk_size=3000)

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

    logger.info("create dev tale")
    tale, errors = fuse_tales(tales_list, code, code_elements_dict)

    if len(errors) > 0:
        logger.info(
            f"We encountered errors while fusing the following \
                    tales for {file_name} - Corrupted tales: {errors}"
        )

    logger.info("add dev tale summary")
    summaries = split_text(str(code_elements_dict["summary"]), chunk_size=9000)
    tale["file_docstring"] = redact_tale_information("top-level", summaries)["text"]

    logger.info(f"save dev tale in: {save_path}")
    with open(save_path, "w") as json_file:
        json.dump(tale, json_file, indent=2)

    if fuse:
        fuse_documentation(code, tale, output_path, file_name, file_ext)

    return tale


def fuse_documentation(code, tale, output_path, file_name, file_ext):
    save_path = os.path.join(output_path, file_name)
    logger.info(f"save fused dev tale in: {save_path}")

    if file_ext == ".py":
        aggregator = PythonAggregator()
    elif file_ext == ".php":
        aggregator = PHPAggregator()
    elif file_ext == ".go":
        aggregator = GoAggregator()

    fused_tale = aggregator.document(code=code, documentation=tale)
    with open(save_path, "w") as file:
        file.write(fused_tale)


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
    "-f",
    "--fuse",
    "fuse",
    is_flag=True,
    default=False,
    help="Adds the docstrings inside the code file.",
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
def main(
    path: str,
    recursive: bool,
    fuse: bool,
    output_path: str = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
):
    load_dotenv()

    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass(
            prompt="Enter your OpenAI API key: "
        )

    if os.path.isdir(path):
        if recursive:
            logger.info("Processing repository")
            process_repository(path, output_path, model_name, fuse)
        else:
            logger.info("Processing folder")
            process_folder(path, output_path, model_name, fuse)
    elif os.path.isfile(path):
        logger.info("Processing file")
        process_file(path, output_path, model_name, fuse)
    else:
        raise f"Invalid input path {path}. Path must be a directory or code file."


if __name__ == "__main__":
    main()
