"""A small FastAPI calculator.

Run with:
    pip install -r requirements.txt
    uvicorn calculator:app --reload

Then open http://127.0.0.1:8000 in your browser.
"""

import ast
import math
import operator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Calculator")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Only these operators are allowed, so users can't run arbitrary Python code.
BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def evaluate(expression: str) -> float:
    """Safely evaluate a math expression like "2 * (3 + 4)"."""
    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("Exponent too large")
        return BINARY_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
        return UNARY_OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Unsupported expression")


class CalcRequest(BaseModel):
    expression: str = Field(..., max_length=200, examples=["2 * (3 + 4)"])


class CalcResponse(BaseModel):
    expression: str
    result: float


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/calc", response_model=CalcResponse)
def calc(request: CalcRequest) -> CalcResponse:
    try:
        # float() also rejects complex results such as (-8) ** 0.5
        result = float(evaluate(request.expression))
    except ZeroDivisionError:
        raise HTTPException(status_code=400, detail="Cannot divide by zero")
    except (SyntaxError, ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid expression: {exc}")

    if not math.isfinite(result):
        raise HTTPException(status_code=400, detail="Result is not a real number")

    return CalcResponse(expression=request.expression, result=result)
