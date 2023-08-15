import re


class PHPAggregator:
    def __init__(self):
        pass

    def document(self, documentation, code):
        documented_code = code
        documented_code = self._document_functions(documentation, documented_code)
        documented_code = self._document_classes(documentation, documented_code)
        return documented_code

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
                    php_docstring = self._format_docstring(method_docstring)
                    code = (
                        code[:insertion_index] + php_docstring + code[insertion_index:]
                    )
        return code

    def _document_classes(self, documentation, code):
        for class_data in documentation["classes"]:
            class_name = class_data["class_name"]
            class_docstring = class_data["class_docstring"]

            pattern = re.compile(r"class\s+" + class_name + r"\s*")
            match = pattern.search(code)

            if match:
                php_docstring = self._format_docstring(class_docstring)
                code = code[: match.start()] + php_docstring + code[match.start() :]
        return code

    def _format_docstring(self, docstring):
        lines = docstring.split("\n")
        php_docstring = "\n/**\n"
        for line in lines:
            php_docstring += " * " + line.strip() + "\n"
        php_docstring += " */\n"
        return php_docstring
