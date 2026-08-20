"""Safe arithmetic evaluator with no eval/exec and strict resource limits."""

from __future__ import annotations

import ast
import math
import operator
from typing import Callable


_BINARY: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def calculate(expression: str) -> dict[str, float | int | str]:
    if len(expression) > 200:
        raise ValueError("expression is too long")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError("invalid arithmetic syntax") from error
    if sum(1 for _ in ast.walk(tree)) > 50:
        raise ValueError("expression is too complex")
    result = _evaluate(tree.body)
    if not math.isfinite(float(result)):
        raise ValueError("result must be finite")
    return {"expression": expression, "result": result}


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _evaluate(node.operand)
        return operand if isinstance(node.op, ast.UAdd) else -operand
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 10 or abs(left) > 1_000_000):
            raise ValueError("power operation exceeds safety limits")
        result = _BINARY[type(node.op)](left, right)
        if abs(float(result)) > 1e15:
            raise ValueError("result exceeds safety limit")
        return result
    raise ValueError("only numeric literals and + - * / // % ** parentheses are allowed")
