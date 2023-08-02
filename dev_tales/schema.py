from typing import List

from pydantic import BaseModel, Field


class ClassEntities(BaseModel):
    class_name: str = Field(default=None, description="Name of the class definition.")
    class_docstring: str = Field(
        default=None,
        description="Docstring that provides an explanation of the purpose of the \
        class.",
    )


class MethodEntities(BaseModel):
    method_name: str = Field(
        default=None, description="Name of the method/function definition."
    )
    method_docstring: str = Field(
        default=None,
        description="Docstring that provides an explanation of the purpose of the \
        method/function.",
    )


class FileDocumentation(BaseModel):
    file_docstring: str = Field(
        default=None,
        description="File-level docstring to be added at the top level of the file \
        explaining what this code does.",
    )
    classes: List[ClassEntities] = Field(
        default=None,
        description="Entities containing class definitions along with their respective \
        docstrings.",
    )
    methods: List[MethodEntities] = Field(
        default=None,
        description="Entities containing method/function definitions along with their \
        respective docstrings.",
    )
