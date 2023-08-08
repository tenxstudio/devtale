from typing import List

from pydantic import BaseModel, Field


class ClassEntities(BaseModel):
    class_name: str = Field(default=None, description="Name of the class definition.")
    class_docstring: str = Field(
        default=None,
        description="Google Style Docstring text that provides an explanation of the \
        purpose of the class, including its arguments if any. All inside the same str.",
    )


class MethodEntities(BaseModel):
    method_name: str = Field(
        default=None, description="Name of the method/function definition."
    )
    method_docstring: str = Field(
        default=None,
        description="Google Style Docstring text that provides an explanation of the \
        purpose of the method/function, including its arguments, returns, and raises \
        if any. All inside the same str.",
    )


class FileDocumentation(BaseModel):
    classes: List[ClassEntities] = Field(
        default=None,
        description="List of entities containing class definitions along with their \
        respective docstrings. This list does not include imports, utility classes, or \
        class instances.",
    )
    methods: List[MethodEntities] = Field(
        default=None,
        description="List of entities containing method/function definitions along \
        with their respective docstrings. This list does not include imports or \
        method/function instances.",
    )
