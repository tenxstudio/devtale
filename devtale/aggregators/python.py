import ast
import re


class Placeholder(ast.NodeTransformer):
    def visit_ClassDef(self, node):
        docstring = ast.Expr(ast.Str(f"CLASS DOCSTRING PLACEHOLDER {node.name}"))
        if not node.body or not isinstance(node.body[0], ast.Expr):
            node.body = [docstring] + node.body
        return node

    def visit_FunctionDef(self, node):
        docstring = ast.Expr(ast.Str(f"METHOD DOCSTRING PLACEHOLDER {node.name}"))
        if not node.body or not isinstance(node.body[0], ast.Expr):
            node.body = [docstring] + node.body
        return node


class pythonAggregator:
    def __init__(self):
        pass

    def document(self, documentation, code):
        code_w_placeholders = self._add_placeholders(code)
        code_definitions = self._get_code_definitions(code_w_placeholders)
        documented_code = code

        for name, definition in code_definitions.items():
            splited_definition = definition.split()
            prefix = splited_definition[0]
            postfix = splited_definition[-1]

            pattern = r"" + prefix + "\s+" + name + "[\s\S]*? " + postfix
            type_item = "method" if prefix == "def" else "class"
            docstring = self._get_docstring(type_item, name, documentation)

            match = re.findall(pattern, documented_code)[0]
            modified_match = match + f'\n"""{docstring}"""'
            documented_code = re.sub(re.escape(match), modified_match, documented_code)

        return documented_code

    def _add_placeholders(self, code: str):
        code_tree = ast.parse(code)
        placeholder_adder = Placeholder()
        modified_ast = placeholder_adder.visit(code_tree)
        modified_code = ast.unparse(modified_ast)

        return modified_code

    def _get_code_definitions(self, code_w_placeholders):
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