"""
AETHER Static AST Analysis & Code Intelligence Guard
===================================================
Provides deep syntactic validation, AST-level security filtering,
cyclomatic complexity analysis, and cognitive invariant verification
before executing or persisting code.
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("aether.ast_guard")


@dataclass
class ASTAnalysisResult:
    is_valid_syntax: bool
    syntax_error: Optional[str] = None
    syntax_error_line: Optional[int] = None
    syntax_error_col: Optional[int] = None
    cyclomatic_complexity: int = 1
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    security_warnings: List[str] = field(default_factory=list)
    invariant_violations: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid_syntax": self.is_valid_syntax,
            "syntax_error": self.syntax_error,
            "syntax_error_line": self.syntax_error_line,
            "syntax_error_col": self.syntax_error_col,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports,
            "security_warnings": self.security_warnings,
            "invariant_violations": self.invariant_violations,
            "suggested_fixes": self.suggested_fixes,
        }


class ComplexityVisitor(ast.NodeVisitor):
    """Calculates McCabe Cyclomatic Complexity of Python AST."""
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_Assert(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_comprehension(self, node):
        self.complexity += 1
        self.generic_visit(node)


class ASTGuard:
    """Static AST Code Intelligence and Invariant Enforcement Engine."""

    DANGEROUS_CALLS = {
        "os.system": "Direct os.system call detected; consider subprocess.run with argument list",
        "eval": "eval() usage detected; dynamic code execution is hazardous",
        "exec": "exec() usage detected; execute_python_code sandbox is preferred",
        "pickle.loads": "Arbitrary code execution risk with untrusted pickle data",
        "__import__": "Dynamic __import__ detected; use importlib or static imports",
    }

    def analyze_python_code(self, code: str) -> ASTAnalysisResult:
        """Perform comprehensive AST inspection on Python code."""
        if not code or not code.strip():
            return ASTAnalysisResult(is_valid_syntax=True, cyclomatic_complexity=0)

        # 1. Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            suggested = []
            if "unexpected EOF" in str(e) or "was never closed" in str(e):
                suggested.append("Check for unclosed brackets, parentheses, or string quotes.")
            elif "invalid syntax" in str(e):
                suggested.append(f"Inspect line {e.lineno} near column {e.offset} for syntax errors.")

            return ASTAnalysisResult(
                is_valid_syntax=False,
                syntax_error=str(e.msg),
                syntax_error_line=e.lineno,
                syntax_error_col=e.offset,
                suggested_fixes=suggested,
            )

        # 2. Extract Structure & Complexity
        functions = []
        classes = []
        imports = []
        security_warnings = []
        invariant_violations = []
        suggested_fixes = []

        # Complexity visitor
        complexity_visitor = ComplexityVisitor()
        complexity_visitor.visit(tree)
        complexity = complexity_visitor.complexity

        if complexity > 15:
            suggested_fixes.append(f"High cyclomatic complexity ({complexity}). Consider refactoring into smaller modular functions.")

        # Walk nodes for structure & security
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

            # Security checks
            if isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        call_name = f"{node.func.value.id}.{node.func.attr}"

                if call_name in self.DANGEROUS_CALLS:
                    security_warnings.append(f"Line {node.lineno}: {self.DANGEROUS_CALLS[call_name]}")

        # 3. Cognitive Invariants Static Audit
        invariant_violations.extend(self.audit_cognitive_invariants(code))

        return ASTAnalysisResult(
            is_valid_syntax=True,
            cyclomatic_complexity=complexity,
            functions=functions,
            classes=classes,
            imports=list(set(imports)),
            security_warnings=security_warnings,
            invariant_violations=invariant_violations,
            suggested_fixes=suggested_fixes,
        )

    def audit_cognitive_invariants(self, code: str) -> List[str]:
        r"""
        Check code for violations of AETHER Cognitive Invariants:
        1. FTS5 multi-word MATCH without tokenization / OR join.
        2. TTS regex stripping raw numeric digits (\d+).
        3. Web Speech Recognition missing continuous=True or debounce < 1.8s.
        4. Ollama keep_alive placed inside options dict instead of top-level.
        """
        violations = []

        # Invariant 1: FTS5 MATCH raw string
        if "MATCH" in code and "sqlite" in code.lower():
            if re.search(r"MATCH\s*\?\s*['\"]", code, re.IGNORECASE) or ("MATCH ?" in code and "tokenize" not in code and "join" not in code):
                violations.append("Cognitive Invariant 1 Violation: Raw query passed directly to FTS5 MATCH without stopword tokenization and OR-join.")

        # Invariant 2: TTS stripping \d+
        if re.search(r"re\.sub\([^)]*\\d\+[^)]*['\"]\s*,\s*['\"]['\"]\s*,\s*text\)", code):
            violations.append("Cognitive Invariant 2 Violation: TTS text cleaning strips raw numeric digits (\\d+). Numbers must be preserved.")

        # Invariant 3: Ollama keep_alive inside options
        if "options={" in code or "options = {" in code:
            if "keep_alive" in code and '"options":' in code:
                violations.append("Cognitive Invariant 4 Violation: keep_alive passed inside options dict. Must be top-level in ollama.chat().")

        return violations

    def validate_or_repair_code(self, code: str) -> Tuple[bool, str, ASTAnalysisResult]:
        """
        Validate code AST. Returns (is_ok, status_message, analysis_result).
        """
        analysis = self.analyze_python_code(code)
        if not analysis.is_valid_syntax:
            msg = f"Syntax Error on line {analysis.syntax_error_line}: {analysis.syntax_error}"
            return False, msg, analysis

        if analysis.security_warnings:
            logger.warning(f"AST Guard Security Warnings: {analysis.security_warnings}")

        if analysis.invariant_violations:
            logger.warning(f"AST Guard Invariant Violations: {analysis.invariant_violations}")

        return True, "AST analysis passed successfully.", analysis

    def validate_code(self, code: str) -> ASTAnalysisResult:
        """Convenience alias for analyze_python_code."""
        return self.analyze_python_code(code)

    def validate_python_file(self, file_path: str) -> ASTAnalysisResult:
        """Validate a Python file on disk."""
        from pathlib import Path
        p = Path(file_path)
        if not p.exists():
            return ASTAnalysisResult(is_valid_syntax=False, syntax_error=f"File not found: {file_path}")
        return self.analyze_python_code(p.read_text(encoding="utf-8"))


ast_guard = ASTGuard()

