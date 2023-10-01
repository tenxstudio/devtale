import re


class GoAggregator:
    def __init__(self):
        pass

    def document(self, documentation, code):
        documented_code = code
        documented_code = self._document_file(documentation, documented_code)
        documented_code = self._add_docstrings(
            documentation, documented_code, type="method"
        )
        documented_code = self._add_docstrings(
            documentation, documented_code, type="class"
        )
        return documented_code

    def _add_docstrings(self, documentation, code, type="method"):
        if type == "method":
            pattern = r"func \([\w\s\*]+\) (\w+)[^\n]*{|\bfunc (\w+)[^\n]*{"
            docstrings = {
                item["method_name"]: item["method_docstring"]
                for item in documentation["methods"]
            }
        else:
            pattern = r"type\s+([A-Z][a-zA-Z0-9_]*)\s+(struct|interface)\s*\{"
            docstrings = {
                item["class_name"]: item["class_docstring"]
                for item in documentation["classes"]
            }

        updated_code_lines = []
        matches = re.finditer(pattern, code)
        last_end = 0

        for match in matches:
            name = match.group(1) or match.group(2)
            index = match.start()

            opening_brace_index = code.find("{", index)

            if opening_brace_index != -1:
                signature = code[index : opening_brace_index + 1]
                lines_before = code[:index].split("\n")[-3:]
                existing_docstring = any(
                    line.strip().startswith("//") or "*/" in line
                    for line in lines_before
                )

                if name in docstrings:
                    docstring = docstrings[name]
                    if not existing_docstring:
                        fixed_docstring = self._break_large_strings(docstring)

                        signature = f"{fixed_docstring}\n{signature}"

                updated_code_lines.append(code[last_end:index])
                updated_code_lines.append(signature)
                last_end = opening_brace_index + 1

        # append any remaining code
        updated_code_lines.append(code[last_end:])
        documented_code = "".join(updated_code_lines)
        return documented_code

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

        return "\n".join(["// " + line for line in lines])

    def _document_file(self, documentation, code):
        """Add a top-level docstring if there isn't one already."""
        file_description = self._break_large_strings(documentation["file_docstring"])
        words = code.split()
        if words[0] != "//" and words[0] != "/*":
            code = file_description + "\n" + code

        return code
