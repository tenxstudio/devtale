from typing import List

from pydantic import BaseModel, Field


class ClassEntities(BaseModel):
    class_name: str = Field(default=None, description="Name of the class definition.")
    class_docstring: str = Field(
        default=None,
        description="Google Style Docstring text that provides an explanation of the \
        purpose of the class and its class args. All inside the same str.",
    )


class MethodEntities(BaseModel):
    method_name: str = Field(
        default=None, description="Name of the method/function definition."
    )
    method_docstring: str = Field(
        default=None,
        description="Google Style Docstring text that provides an explanation of the \
        purpose of the method/function, method args, method returns, and method \
        raises. All inside the same str.",
    )


class FileDocumentation(BaseModel):
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
