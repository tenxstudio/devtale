import ast
import re


class Placeholder(ast.NodeTransformer):
    def visit(self, node):
        if isinstance(node, ast.ClassDef):
            docstring = ast.Expr(ast.Str(f"CLASS DOCSTRING PLACEHOLDER {node.name}"))
            if not node.body or not isinstance(node.body[0], ast.Expr):
                node.body = [docstring] + node.body

        elif isinstance(node, ast.FunctionDef):
            docstring = ast.Expr(ast.Str(f"METHOD DOCSTRING PLACEHOLDER {node.name}"))
            if not node.body or not isinstance(node.body[0], ast.Expr):
                node.body = [docstring] + node.body
        else:
            pass

        return self.generic_visit(node)


class PythonAggregator:
    def __init__(self):
        pass

    def document(self, documentation, code):
        code = self._add_file_level_docstring(code, documentation)
        code_w_placeholders = self._add_placeholders(code)
        code_definitions = self._get_code_definitions(code_w_placeholders)
        documented_code = code

        # For each function/method or class definition we found using AST, we match
        # it with the dev tale info.
        for name, definition in code_definitions.items():
            splited_definition = definition.split()

            prefix = splited_definition[0]  # def, class
            postfix = splited_definition[-1]  # last text Eg. "->None", "):", etc

            type_item = "method" if prefix == "def" else "class"
            # Extract only the last character if we have conflicting text that won't
            # allow us to match the pattern.
            if len(splited_definition) == 2 or "'" in postfix or '"' in postfix:
                postfix = postfix[-1]

            pattern = r"" + prefix + "\s+" + name + "[\s\S]*?" + re.escape(postfix)

            docstring = self._get_docstring(type_item, name, documentation)

            # docstring = self._fix_docstring(docstring)
            docstring = self._break_large_strings(docstring)
            comment = f'\n"""{docstring}"""'
            match = re.findall(pattern, documented_code)

            if match:
                # use ast to reformat code into lines, trick to make the search easier
                match = match[0]
                parsed_text = ast.parse(code)
                unparsed_text = ast.unparse(parsed_text)

                indentation_size = self._extract_indentation(unparsed_text, definition)

                # add identation to the docstrings
                lines = comment.split("\n")
                indented_lines = [
                    f"{' ' * indentation_size}{line.strip()}" if line.strip() else line
                    for line in lines
                ]
                comment = "\n".join(indented_lines)

                # add the docstring
                documented_code = re.sub(
                    re.escape(match), match + comment, documented_code
                )

        return documented_code

    def _add_file_level_docstring(self, code: str, documentation):
        """Add a top-level docstring if there isn't one already."""
        file_description = self._break_large_strings(documentation["file_docstring"])
        docstring = f'"""{file_description}\n"""\n'

        words = code.split()
        if words[0] != '"""' and words[0] != "#":
            code = docstring + "\n" + code

        return code

    def _add_placeholders(self, code: str):
        """AST is capable of adding docstrings to the code; however, it reformats
        the file. To avoid this, we add a placeholder that we later search for in
        the process. This helps us determine the location where the docstring
        should be attached.
        """
        code_tree = ast.parse(code)
        placeholder_adder = Placeholder()
        modified_ast = placeholder_adder.visit(code_tree)
        modified_code = ast.unparse(modified_ast)

        return modified_code

    def _get_code_definitions(self, code_w_placeholders):
        """Search for the placeholder we added and extract the function/method or
        class signature.
        """
        code_definitions = {}
        lines = code_w_placeholders.splitlines()

        for idx, line in enumerate(lines):
            if line.strip().startswith('"""METHOD DOCSTRING PLACEHOLDER'):
                name = line.split()[-1].replace('"""', "")
                code_definitions[name] = lines[idx - 1]
            elif line.strip().startswith('"""CLASS DOCSTRING PLACEHOLDER'):
                name = line.split()[-1].replace('"""', "")
                code_definitions[name] = lines[idx - 1]
        return code_definitions

    def _get_docstring(self, type_item: str, name: str, documentation):
        if type_item == "method":
            method_info = next(
                (
                    method
                    for method in documentation["methods"]
                    if method["method_name"] == name
                ),
                None,
            )
            if method_info:
                return method_info["method_docstring"]
        elif type_item == "class":
            class_info = next(
                (cls for cls in documentation["classes"] if cls["class_name"] == name),
                None,
            )
            if class_info:
                return class_info["class_docstring"]
        return ""

    def _extract_indentation(self, text, code_line):
        lines = text.split("\n")
        next_code_line = None

        for idx, line in enumerate(lines):
            if code_line in line:
                for i in range(idx + 1, len(lines)):
                    next_line = lines[i]
                    if next_line.strip():
                        next_code_line = next_line
                        break
                break

        indentation_size = (
            len(next_code_line) - len(next_code_line.lstrip()) if next_code_line else 0
        )
        return indentation_size

    def _break_large_strings(self, string, max_lenght=90):
        """Avoid very long in-line comments by breaking them into smaller
        segments with a maximum length.
        """
        words = string.split()
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

    def _fix_docstring(self, docstring):
        pattern = r"^(.*?)(?=Args:|Returns:|$)"
        match = re.search(pattern, docstring, re.DOTALL)
        if match:
            extracted_summary = match.group(1).strip()
            fixed_extracted_summary = self._break_large_strings(extracted_summary)

            rest_of_docstring = docstring[match.end() :]

            fixed_docstring = fixed_extracted_summary + "\n\n" + rest_of_docstring
            return fixed_docstring
        else:
            return ""
