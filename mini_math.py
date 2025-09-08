# mini_math.py
from __future__ import annotations
import ast, re

_ALLOWED = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Load, ast.Tuple, ast.List, ast.Subscript,
    ast.Index,  # harmless in 3.11-, ignored in 3.12+
)

def _safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ValueError(f"disallowed node: {type(node).__name__}")
        # forbid names/calls entirely
        if isinstance(node, (ast.Name, ast.Call, ast.Attribute)):
            raise ValueError("names/calls not allowed")
    return eval(compile(tree, "<math>", "eval"), {"__builtins__": {}}, {})

def solve_if_simple(text: str) -> tuple[bool, str]:
    # keep only digits, ops, space, and parentheses; normalize ^ → **; kill commas
    raw = re.sub(r"[^0-9\.\+\-\*/\^\(\)\s]", " ", text)
    expr = re.sub(r",", "", raw).strip()
    if not re.search(r"[+\-*/^]", expr):           # must have an operator
        return False, ""
    expr = expr.replace("^", "**")
    try:
        val = _safe_eval(expr)
        if isinstance(val, float) and val.is_integer():
            val = int(val)
        return True, str(val)
    except Exception:
        return False, ""

def pick_final_answer(text: str) -> str:
    # prefer the last line that looks like a number; otherwise last non-empty line
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return ""
    for l in reversed(lines):
        m = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", l)
        if m:
            return m.group(0)
    return lines[-1]
