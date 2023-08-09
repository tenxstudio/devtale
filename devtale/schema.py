from typing import List

from pydantic import BaseModel, Field


class ClassEntities(BaseModel):
    class_name: str = Field(default=None, description="Name of the class")
    class_docstring: str = Field(
        default=None,
        description="The Google Style Docstring text that provides an explanation \
         of the purpose of the class, including its arguments if any. All inside  \
         the same str.",
    )


class MethodEntities(BaseModel):
    method_name: str = Field(default=None, description="Name of the method")
    method_docstring: str = Field(
        default=None,
        description="The Google Style Docstring text that provides an explanation \
        of the purpose of the method, including its arguments, returns, and raises \
        if any. All inside the same str.",
    )


class FileDocumentation(BaseModel):
    classes: List[ClassEntities] = Field(
        default=None,
        description="List of entities containing classes names along with their \
        respective docstrings.",
    )
    methods: List[MethodEntities] = Field(
        default=None,
        description="List of entities containing method names along with with \
        their respective docstrings.",
    )
