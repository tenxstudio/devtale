from langchain.text_splitter import Language

# we are only documenting the file that ends with the following extensions:
ALLOWED_EXTENSIONS = [".js", ".go", ".php", ".py"]
ALLOWED_NO_CODE_EXTENSIONS = ["", ".sh", ".xml", ".yaml", ".yml"]

# split code files according the programming language
LANGUAGES = {
    ".php": Language.PHP,
    ".py": Language.PYTHON,
    ".go": Language.GO,
    ".js": Language.JS,
}

DOCSTRING_LABEL = "@DEVTALE-GENERATED:"
