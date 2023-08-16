import re


class PHPAggregator:
    def __init__(self):
        pass

    def document(self, documentation, code):
        documented_code = code
        documented_code = self._document_file(documentation, documented_code)
        documented_code = self._document_functions(documentation, documented_code)
        documented_code = self._document_classes(documentation, documented_code)
        return documented_code

    def _document_file(self, documentation, code):
        file_description = documentation["file_docstring"]
        docstring = self._format_docstring(file_description, 0)

        code = docstring + "\n" + code

        return code

    def _document_functions(self, documentation, code):
        for method_data in documentation["methods"]:
            method_name = method_data["method_name"]
            method_docstring = method_data["method_docstring"]

            pattern = re.compile(r"function\s+" + method_name + r"\s*")
            match = pattern.search(code)

            if match:
                words = code[max(0, match.start() - 50) : match.start()].split()[-3:]
                if words[-1] == "static":
                    if (
                        words[-2] in ["public", "protected", "private"]
                        and words[-3] != "*/"
                    ):
                        insertion_index = max(0, match.start() - len(words[-2]) - 1)
                    else:
                        insertion_index = None
                elif words[-1] in ["public", "protected", "private"]:
                    if words[-2] != "*/":
                        insertion_index = max(0, match.start() - len(words[-1]) - 1)
                    else:
                        insertion_index = None
                elif words[-1] != "*/":
                    insertion_index = max(0, match.start())
                else:
                    insertion_index = None

                if insertion_index:
                    indentation = self._extract_indentation(code, match.group(0))
                    php_docstring = self._format_docstring(
                        method_docstring, indentation
                    )
                    code = (
                        code[:insertion_index]
                        + php_docstring
                        + " " * indentation
                        + code[insertion_index:]
                    )
        return code

    def _document_classes(self, documentation, code):
        for class_data in documentation["classes"]:
            class_name = class_data["class_name"]
            class_docstring = class_data["class_docstring"]

            pattern = re.compile(r"class\s+" + class_name + r"\s*")
            match = pattern.search(code)

            if match:
                indentation = self._extract_indentation(code, match.group(0))
                php_docstring = self._format_docstring(class_docstring, indentation)
                code = (
                    code[: match.start()]
                    + php_docstring
                    + " " * indentation
                    + code[match.start() :]
                )
        return code

    def _format_docstring(self, docstring, indentation):
        lines = docstring.split("\n")
        php_docstring = "\n" + " " * indentation + "/**\n"
        for line in lines:
            php_docstring += " " * indentation + " * " + line.strip() + "\n"
        php_docstring += " " * indentation + " */\n"
        return php_docstring

    def _extract_indentation(self, text, code_line):
        lines = text.split("\n")
        match_line = None
        for line in lines:
            if code_line in line:
                match_line = line
                break
        indentation = 0
        if match_line:
            for char in match_line:
                if char == "\t":
                    indentation += 4
                elif char == " ":
                    indentation += 1
                else:
                    break
        return indentation
