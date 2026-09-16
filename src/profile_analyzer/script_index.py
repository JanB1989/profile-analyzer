"""Small, non-evaluating Clausewitz script indexer for profiler source context.

This is deliberately a structural reader, not a game database/load-order engine.
It records assignment ancestry and literal references, respecting comments,
quoted strings, operators, typed blocks and anonymous list blocks. The caller
masks inline arithmetic and declaration prefixes without moving source lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    value: str
    line: int


LEXEME = re.compile(
    r'(?P<space>\s+)|(?P<comment>\#[^\n]*)|'
    r'(?P<string>"(?:\\.|[^"\\])*")|'
    r'(?P<open>\{)|(?P<close>\})|'
    r'(?P<op>\?=|==|!=|<=|>=|=|<|>)|'
    r'(?P<atom>[^\s{}#"<>=!]+)'
)


def tokenize(text: str) -> list[Token]:
    tokens = []
    offset, line = 0, 1
    while offset < len(text):
        match = LEXEME.match(text, offset)
        if match is None:
            raise ValueError(f"Unexpected character or unterminated string at line {line}")
        kind, value = match.lastgroup, match.group()
        if kind not in ("space", "comment"):
            if kind == "string":
                # Only decode escaped quotes/backslashes; do not reinterpret
                # literal \n or Windows paths in script names or values.
                value = re.sub(r'\\(["\\])', r'\1', value[1:-1])
            tokens.append(Token(kind, value, line))
        line += match.group().count("\n")
        offset = match.end()
    return tokens


def index_entries(text: str) -> list[dict]:
    tokens = tokenize(text)
    entries = []
    # Anonymous blocks inherit their surrounding assignment owner.
    stack: list[int | None] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        parent = stack[-1] if stack else None
        if token.kind == "close":
            if not stack:
                raise ValueError(f"Unexpected closing brace at line {token.line}")
            stack.pop()
            i += 1
            continue
        if token.kind == "open":
            stack.append(parent)
            i += 1
            continue
        if token.kind in ("atom", "string") and i + 1 < len(tokens) and tokens[i + 1].kind == "op":
            if i + 2 >= len(tokens) or tokens[i + 2].kind in ("close", "op"):
                raise ValueError(f"Missing assignment value at line {token.line}")
            value = tokens[i + 2]
            entry_id = len(entries)
            entries.append({
                "line": token.line, "key": token.value,
                "value": value.value if value.kind in ("atom", "string") else "",
                "parent": parent,
                "symbol": entries[parent]["symbol"] if parent is not None else token.value,
            })
            i += 3
            if value.kind == "open":
                stack.append(entry_id)
            elif i < len(tokens) and tokens[i].kind == "open":
                # Typed values such as color = hsv { ... }.
                stack.append(entry_id)
                i += 1
            continue
        if token.kind == "op":
            raise ValueError(f"Unexpected operator at line {token.line}")
        if not stack:
            raise ValueError(f"Expected assignment at line {token.line}")
        i += 1  # scalar item in a list
    if stack:
        raise ValueError("Unexpected end of file inside block")
    return entries
