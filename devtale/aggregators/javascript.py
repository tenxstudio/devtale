import re


class JavascriptAggregator:
    def __init__(self):
        pass

    def document(self, documentation, code):
        documented_code = code
        documented_code = self._document_file(documentation, documented_code)
        documented_code = self._add_docstrings(
            documentation, documented_code, type="methods"
        )
        documented_code = self._add_tsx_docstrings(documentation, documented_code)
        documented_code = self._add_docstrings(
            documentation, documented_code, type="classes"
        )
        return documented_code

    def _add_docstrings(self, documentation, code, type="methods"):
        if type == "methods":
            entities = documentation["methods"]
        else:
            entities = documentation["classes"]

        lines = code.splitlines()
        previous_line = None

        for entity in entities:
            name_to_search = (
                entity["method_name"] if type == "methods" else entity["class_name"]
            )
            docstring = (
                entity["method_docstring"]
                if type == "methods"
                else entity["class_docstring"]
            )

            if type == "methods":
                pattern = (
                    r"^\s*(?:"
                    + re.escape(name_to_search)
                    + r")\s*\([^)]*\)\s*{|function\s+"
                    + re.escape(name_to_search)
                    + r"\s*\("
                )
            else:
                pattern = r"class\s+" + re.escape(name_to_search)

            for i, line in enumerate(lines):
                if re.findall(pattern, line, re.MULTILINE):
                    if previous_line:
                        # Check if the function or class is already documented
                        if "*/" not in previous_line and "//" not in previous_line:
                            indentation = self._extract_indentation(line)
                            fixed_docstring = self._break_large_strings(docstring)
                            fixed_docstring = self._format_docstring(
                                fixed_docstring, indentation
                            )
                            lines.insert(i, fixed_docstring)
                            break
                elif line.strip():
                    previous_line = line

        return "\n".join(lines)

    def _add_tsx_docstrings(self, documentation, code):
        entities = documentation["methods"]
        lines = code.splitlines()
        previous_line = None

        for entity in entities:
            name_to_search = entity["method_name"]
            docstring = entity["method_docstring"]

            pattern = (
                r""
                + re.escape(name_to_search)
                + "\s*=\s*(\(\s*\)\s*=>\s*{|\(\s*([^)]*)\s*\)\s*=>)|"
                + re.escape(name_to_search)
                + r"\(\)\s*=>\s*{\)"
            )

            for i, line in enumerate(lines):
                if re.findall(pattern, line, re.MULTILINE):
                    if previous_line:
                        # Check if the function or class is already documented
                        if "*/" not in previous_line and "//" not in previous_line:
                            indentation = self._extract_indentation(line)
                            fixed_docstring = self._break_large_strings(docstring)
                            fixed_docstring = self._format_docstring(
                                fixed_docstring, indentation
                            )
                            lines.insert(i, fixed_docstring)
                            break
                elif line.strip():
                    previous_line = line

        return "\n".join(lines)

    def _extract_indentation(self, code_line):
        indentation = 0
        for char in code_line:
            if char == "\t":
                indentation += 4
            elif char == " ":
                indentation += 1
            else:
                break
        return indentation

    def _format_docstring(self, docstring, indentation):
        """Add the in-line comment character key"""
        lines = docstring.split("\n")
        js_docstring = "\n" + " " * indentation + "/*\n"
        for line in lines:
            js_docstring += " " * indentation + line.strip() + "\n"
        js_docstring += " " * indentation + "*/"
        return js_docstring

    def _document_file(self, documentation, code):
        """Add a top-level docstring if there isn't one already."""
        file_description = self._break_large_strings(documentation["file_docstring"])
        words = code.split()
        # Check if the file already has a top-file docstring
        if words[0] != "//" and words[0] != "/*" and not words[0].startswith("/*"):
            code = "/*" + file_description + "*/\n" + code

        return code

    def _break_large_strings(self, string, max_lenght=90):
        """Avoid very long in-line comments by breaking them into smaller
        segments with a maximum length.
        """
        words = string.replace("\\n", " \n ").split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_lenght:
                if current_line:
                    current_line += " "
                current_line += word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        return "\n".join([line for line in lines])
