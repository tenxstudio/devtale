from langchain.text_splitter import Language

# we are only documenting the file that ends with the following extensions:
ALLOWED_EXTENSIONS = [".go", ".php", ".py", ""]

# split code files according the programming language
LANGUAGES = {
    ".php": Language.PHP,
    ".py": Language.PYTHON,
    ".go": Language.GO,
    ".cpp": Language.CPP,
    ".java": Language.JAVA,
    ".js": Language.JS,
}

# indeitifers used to add documentation into the files.
IDENTIFIERS = {
    "php": [["class"], ["function"]],
    "python": [["class"], ["def"]],
    "go": [["struct"], ["func"]],
    "cpp": [["class"], ["void", "int", "float", "double"]],
    "java": [["class"], ["public", "protected", "private", "static"]],
    "js": [["class"], ["function", "const", "let", "var"]],
}
