import copy
import getpass
import json
import logging
import os

import click
from dotenv import find_dotenv, load_dotenv

from devtale.constants import (
    ALLOWED_EXTENSIONS,
    ALLOWED_NO_CODE_EXTENSIONS,
    DOCSTRING_LABEL,
    LANGUAGES,
)
from devtale.utils import (
    build_project_tree,
    extract_code_elements,
    fuse_documentation,
    fuse_tales_chunks,
    get_unit_tale,
    prepare_code_elements,
    redact_tale_information,
    split_code,
    split_text,
)

DEFAULT_OUTPUT_PATH = "devtale_demo/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_repository(
    root_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    fuse: bool = False,
    debug: bool = False,
    cost_estimation: bool = False,
) -> None:
    """It creates a dev tale for each file in the repository, and it
    generates a README for the whole repository.
    """
    cost = 0
    folder_tales = {
        "repository_name": os.path.basename(os.path.abspath(root_path)),
        "folders": [],
    }

    # Extract the content of the original README if there is one already.
    original_readme_content = None
    for file_name in ["readme.md", "README.md"]:
        readme_path = os.path.join(root_path, file_name)
        if os.path.exists(readme_path):
            with open(readme_path, "r") as file:
                original_readme_content = file.readlines()
            if root_path == output_path:
                try:
                    os.rename(readme_path, os.path.join(root_path, "old_readme.md"))
                except OSError as e:
                    logger.info(f"Error keeping the original readme file: {e}")
            break

    # Check if we have a gitignore file to extract the correct project tree
    # and files.
    gitignore_path = os.path.join(root_path, ".gitignore")
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as gitignore_file:
            gitignore_patterns = [
                line.strip() for line in gitignore_file if line.strip()
            ]
    else:
        gitignore_patterns = None

    # Get the project tree before modify it along with the complete list of files
    # that the repository has.
    project_tree, file_paths = build_project_tree(
        root_path, gitignore_patterns=gitignore_patterns
    )
    project_tree = ".\n" + project_tree

    # Extract the folder paths from files list. This allows to avoid processing
    # folders that should be ignored, and to use the process_folder logic.
    folders = list(set([os.path.dirname(file_path) for file_path in file_paths]))

    # sort to always have the root folder at the beggining of the list.
    folders = sorted(folders, key=lambda path: path.count("/"))

    # Get the folder's README section of each folder while it create a dev tale
    # for each file.
    folders_readmes = []
    for folder_path in folders:
        try:
            # Fix folder path to avoid issues with file system.
            if not folder_path.endswith("/"):
                folder_path += "/"

            folder_full_name = os.path.relpath(folder_path, root_path)

            # Generate folder's README, folder's one-line sentence description, and
            # extract the cost of documenting the folder.
            folder_readme, folder_tale, folder_cost = process_folder(
                folder_path=folder_path,
                output_path=os.path.join(output_path, folder_full_name)
                if folder_full_name != "."
                else output_path,
                fuse=fuse,
                debug=debug,
                folder_full_name=folder_full_name,
                cost_estimation=cost_estimation,
            )
            cost += folder_cost

        except Exception as e:
            folder_name = os.path.basename(folder_path)
            logger.info(
                f"Failed to create folder-level tale for {folder_name} - Exception: {e}"
            )
            folder_tale = None

        # Create a dictionary with the folder's info that serves as context for
        # generating the main repository README.
        if folder_tale:
            folders_readmes.append("\n\n" + folder_readme)
            # Fix root folder information.
            if folder_path == folders[0]:
                folder_tales["folders"].append(
                    {
                        "folder_name": os.path.basename(os.path.abspath(root_path)),
                        "folder_summary": folder_tale,
                        "is_the_root_folder": True,
                    }
                )
            else:
                folder_tales["folders"].append(
                    {
                        "folder_name": folder_full_name,
                        "folder_summary": folder_tale,
                    }
                )

    # For debugging, we only care in seeing the files input workflow
    if debug:
        logger.debug(f"FOLDER_TALES: {folder_tales}")
        return None

    if folder_tales:
        # Generate main README using as context the folders summaries.
        folder_summaries = split_text(str(folder_tales), chunk_size=15000)
        root_readme, call_cost = redact_tale_information(
            "root-level",
            folder_summaries,
            model_name="gpt-3.5-turbo-16k",
            cost_estimation=cost_estimation,
        )
        cost += call_cost

        # Because of the template, GPT might also add the line separator, so we need
        # to clean.
        root_readme = root_readme.replace("----------", "")

        # Append the folders README sections.
        if folders_readmes:
            folders_information = "\n\n## Folders" + "".join(folders_readmes)
            root_readme = root_readme + folders_information

        # Append the project tree.
        tree = f"\n\n## Project Tree\n```bash\n{project_tree}```\n\n"
        root_readme = root_readme + tree

        # Append the original readme content as extra notes, removing the header.
        if original_readme_content:
            filtered_original_readme = [
                line for line in original_readme_content if not line.startswith("# ")
            ]
            modified_original_readme = "\n\n## Extra notes\n\n" + "".join(
                filtered_original_readme
            )
            root_readme = root_readme + modified_original_readme

        # save main README if we are not pre-estimating cost.
        if not cost_estimation:
            logger.info("save root json..")
            with open(os.path.join(output_path, "root_level.json"), "w") as json_file:
                json.dump(folder_tales, json_file, indent=2)

            logger.info(f"saving root index in {output_path}")
            with open(
                os.path.join(output_path, "README.md"), "w", encoding="utf-8"
            ) as file:
                file.write(root_readme)

    return cost


def process_folder(
    folder_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    fuse: bool = False,
    debug: bool = False,
    folder_full_name: str = None,
    cost_estimation: bool = False,
) -> None:
    """It creates a dev tale for each file in the directory without exploring
    subdirectories, and it generates a README section for the folder.
    """
    cost = 0
    save_path = os.path.join(output_path, os.path.basename(folder_path))
    tales = []

    # Iterate through each file in the folder
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        # Check it if is a file that we need to process
        if os.path.isfile(file_path) and (
            os.path.splitext(file_name)[1] in ALLOWED_EXTENSIONS
            or os.path.splitext(file_name)[1] in ALLOWED_NO_CODE_EXTENSIONS
        ):
            logger.info(f"processing {file_path}")
            # Create dev tale for the file
            try:
                file_tale, file_cost = process_file(
                    file_path, save_path, fuse, debug, cost_estimation
                )
                cost += file_cost
            except Exception as e:
                logger.info(
                    f"Failed to create dev tale for {file_path} - Exception: {e}"
                )
                file_tale = None

            # Create a dictionary with the tale's file_docstrings values to use them
            # as context for the folder's README section
            if file_tale is not None:
                if file_tale["file_docstring"]:
                    if not folder_full_name:
                        folder_full_name = os.path.basename(
                            os.path.abspath(folder_path)
                        )

                    # If this is a root folder, make its name more aesthetic.
                    if folder_full_name == ".":
                        folder_full_name = "./"

                    # Check if we already have the folder_name as key, if yes, then
                    # append the file_docstring on it. Useful when working in a
                    # repository level.
                    folder_entry = next(
                        (
                            item
                            for item in tales
                            if item["folder_name"] == folder_full_name
                        ),
                        None,
                    )
                    if folder_entry is None:
                        folder_entry = {
                            "folder_name": folder_full_name,
                            "folder_files": [],
                        }
                        # Add a generic description in case this is a root directory.
                        if folder_full_name == "./":
                            folder_entry[
                                "folder_description"
                            ] = """
                            This is the root path of the repository. The top-level
                            directory.
                            """

                        tales.append(folder_entry)

                    folder_entry["folder_files"].append(
                        {
                            "file_name": file_name,
                            "file_description": file_tale["file_docstring"],
                        }
                    )

    # For the debugging mode we do not want to generate the folder's README
    # section. We only want to verify the input flow.
    if debug:
        logger.debug(f"FOLDER INFO: folder_path: {folder_path}")
        logger.debug(f"FOLDER INFO: output_path: {output_path}")
        logger.debug(f"FOLDER INFO: save_path: {save_path}")
        logger.debug(f"FILE_TALES: {tales}")
        return "-", "-", cost

    if tales:
        # Generate the folder's README section using as context the tales summaries.
        files_summaries = split_text(str(tales), chunk_size=10000)
        folder_readme, fl_cost = redact_tale_information(
            "folder-level",
            files_summaries,
            model_name="gpt-3.5-turbo-16k",
            cost_estimation=cost_estimation,
        )

        # Because of the template, GPT might also add the line separator, so we need
        # to clean
        folder_readme = folder_readme.replace("----------", "")

        # Generate a folder one-line description using the folder's readme as context.
        # This is a separated call to avoid issues with json attempting to decode
        # markdown text, and its porpuse is to be used as context for the repository
        # mode.
        folder_overview, fd_cost = redact_tale_information(
            "folder-description",
            folder_readme,
            model_name="gpt-3.5-turbo-16k",
            cost_estimation=cost_estimation,
        )

        cost += fl_cost + fd_cost

        # save folder tale if we are not pre-estimating cost.
        if not cost_estimation:
            logger.info("save folder json..")
            with open(os.path.join(save_path, "folder_level.json"), "w") as json_file:
                json.dump(tales, json_file, indent=2)

            logger.info(f"saving index in {save_path}")
            with open(
                os.path.join(save_path, "README.md"), "w", encoding="utf-8"
            ) as file:
                file.write(folder_readme)

        return folder_readme, folder_overview, cost
    return None, None, cost


def process_file(
    file_path: str,
    output_path: str = DEFAULT_OUTPUT_PATH,
    fuse: bool = False,
    debug: bool = False,
    cost_estimation: bool = False,
) -> None:
    """It creates a dev tale for the file input."""
    cost = 0
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[-1]
    save_path = os.path.join(output_path, f"{file_name}.json")

    # For the debugging mode we do not want to process the file, we only want
    # to verify input. Useful to verify the repository/directories flow.
    if debug:
        logger.debug(f"FILE INFO:\nfile_path: {file_path}\nsave_path: {save_path}")
        return {"file_docstring": "-"}, cost

    # Create output dir if it does not exists and only if we are not
    # pre-estimating the cost.
    if not os.path.exists(output_path) and not cost_estimation:
        os.makedirs(output_path)

    logger.info("read dev draft")
    with open(file_path, "r") as file:
        code = file.read()

    # Return empty devtale if the input file is empty.
    if not code:
        return {"file_docstring": ""}, cost

    # Avoid processing a file twice if we already have a tale for it.
    # Only fuse it again. Useful to avoid GPT calls in case of debugging
    # aggregators.
    if os.path.exists(save_path):
        logger.info(f"Skipping {file_name} as its tale file already exists.")
        with open(save_path, "r") as file:
            found_tale = json.load(file)
        if fuse:
            fuse_documentation(
                code=code,
                tale=found_tale,
                file_ext=file_ext,
                save_path=os.path.join(output_path, file_name),
            )
        return found_tale, cost

    # For config/bash files we do not aim to document the file itself. We
    # care about understanding what the file does.
    if not file_ext or file_ext in ALLOWED_NO_CODE_EXTENSIONS:
        # a small single chunk is enough
        no_code_file = split_text(code, chunk_size=5000)[0].page_content
        # prepare input
        no_code_file_data = {
            "file_name": file_name,
            "file_content": no_code_file,
        }
        file_docstring, call_cost = redact_tale_information(
            content_type="no-code-file",
            docs=no_code_file_data,
            model_name="gpt-3.5-turbo",
            cost_estimation=cost_estimation,
        )
        cost += call_cost

        return {"file_docstring": file_docstring}, cost

    # big_docs reduces the number of GPT-4 calls as we want to extract
    # functions/classes names, while short_docs allows GPT-4 to focus in
    # a more granular context to accurately generate the docstring for each
    # function/class that it found.
    logger.info("split dev draft ideas")
    big_docs = split_code(code, language=LANGUAGES[file_ext], chunk_size=10000)
    short_docs = split_code(code, language=LANGUAGES[file_ext], chunk_size=3000)

    logger.info("extract code elements")
    code_elements = []
    for idx, doc in enumerate(big_docs):
        elements_set, call_cost = extract_code_elements(
            big_doc=doc, model_name="gpt-4", cost_estimation=cost_estimation
        )
        cost += call_cost
        if elements_set:
            code_elements.append(elements_set)

    # Combine all the code elements extracted into a single general Dict
    # without duplicates.
    logger.info("prepare code elements")
    code_elements_dict = prepare_code_elements(code_elements)

    # Make a copy to keep the original dict intact.
    code_elements_copy = copy.deepcopy(code_elements_dict)

    # Clean dict copy to remove keys with empty values and the summaries
    # of each code chunk.
    code_elements_copy.pop("summary", None)
    if not code_elements_copy["classes"]:
        code_elements_copy.pop("classes", None)
    if not code_elements_copy["methods"]:
        code_elements_copy.pop("methods", None)

    logger.info("create tale sections")
    tales_list = []
    # Generate a docstring for each class and function/method in the
    # code_elements.
    if code_elements_copy or cost_estimation:
        for idx, doc in enumerate(short_docs):
            tale, call_cost = get_unit_tale(
                short_doc=doc,
                code_elements=code_elements_copy,
                model_name="gpt-4",
                cost_estimation=cost_estimation,
            )
            cost += call_cost
            tales_list.append(tale)
            logger.info(f"tale section {str(idx+1)}/{len(short_docs)} done.")

    # Combine all generated docstrings JSON-formated ouputs into a single,
    # general one.
    logger.info("create dev tale")
    tale, errors = fuse_tales_chunks(tales_list, code, code_elements_dict)

    # Check if we discarded some docstrings.
    if len(errors) > 0:
        logger.info(
            f"We encountered errors while fusing the following \
                    tales for {file_name} - Corrupted tales: {errors}"
        )

    # Generate a top-level docstrings using as context all the summaries we got
    # from each big_doc code chunk output.
    logger.info("add dev tale summary")
    summaries = split_text(str(code_elements_dict["summary"]), chunk_size=9000)

    file_docstring, call_cost = redact_tale_information(
        content_type="top-level",
        docs=summaries,
        model_name="gpt-3.5-turbo",
        cost_estimation=cost_estimation,
    )
    cost += call_cost

    # Add the docstrings in the code file.
    if fuse and not cost_estimation:
        # add devtale label into the top-file summary.
        tale["file_docstring"] = DOCSTRING_LABEL + "\n" + file_docstring
        fused_save_path = os.path.join(output_path, file_name)
        logger.info(f"save fused dev tale in: {fused_save_path}")
        fuse_documentation(code, tale, file_ext, save_path=fused_save_path)

    # Remove devtale label.
    tale["file_docstring"] = file_docstring

    logger.info(f"save dev tale in: {save_path}")
    if not cost_estimation:
        with open(save_path, "w") as json_file:
            json.dump(tale, json_file, indent=2)

    return tale, cost


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
    help="The destination folder where you want to save the documentation outputs. \
        Default: devtale_demo/",
)
@click.option(
    "--debug",
    "debug",
    is_flag=True,
    default=False,
    help="Mock answers avoiding any GPT call.",
)
@click.option(
    "--estimation",
    "cost_estimation",
    is_flag=True,
    default=False,
    help="When true, estimate the cost of openAI's API usage, without making any call.",
)
def main(
    path: str,
    recursive: bool,
    fuse: bool,
    output_path: str = DEFAULT_OUTPUT_PATH,
    debug: bool = False,
    cost_estimation: bool = False,
):
    load_dotenv(find_dotenv(usecwd=True))

    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = getpass.getpass(
            prompt="Enter your OpenAI API key: "
        )

    if os.path.isdir(path):
        if recursive:
            logger.info("Processing repository")
            price = process_repository(
                root_path=path,
                output_path=output_path,
                fuse=fuse,
                debug=debug,
                cost_estimation=cost_estimation,
            )
        else:
            logger.info("Processing folder")
            _, _, price = process_folder(
                folder_path=path,
                output_path=output_path,
                fuse=fuse,
                debug=debug,
                cost_estimation=cost_estimation,
            )
    elif os.path.isfile(path):
        logger.info("Processing file")
        _, price = process_file(
            file_path=path,
            output_path=output_path,
            fuse=fuse,
            debug=debug,
            cost_estimation=cost_estimation,
        )

    else:
        raise f"Invalid input path {path}. Path must be a directory or code file."

    if cost_estimation:
        logger.info(f"Approximate cost: ${price:.5f} USD")
    else:
        logger.info(f"Total cost: ${price:.5f} USD")


if __name__ == "__main__":
    main()
