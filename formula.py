"""Синтаксис формул, общий для ЛР 1 и 2."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Formula:
    symbol: str
    args: tuple[Formula, ...] = ()

    def __str__(self):
        if not self.args:
            return self.symbol
        if self.symbol == "¬":
            return f"¬{self.args[0]}"
        left, right = self.args
        return f"({left} {self.symbol} {right})"

    def variables(self):
        if not self.args:
            return {self.symbol}
        return set().union(*(child.variables() for child in self.args))


ALIASES = {"->": "→", "⊃": "→", "!": "¬", "~": "¬", "&": "∧", "|": "∨"}
PRECEDENCE = {"→": 1, "∨": 2, "∧": 3}


def parse(source: str) -> Formula:
    tokens = [(ALIASES.get(m[0], m[0]), m.start() + 1)
              for m in re.finditer(r"->|\S", source)]
    tokens.append(("", len(source) + 1))
    index = 0

    def expression(minimum):
        nonlocal index
        symbol, position = tokens[index]
        index += 1
        if "a" <= symbol <= "z" and len(symbol) == 1:
            node = Formula(symbol)
        elif symbol == "¬":
            node = Formula(symbol, (expression(4),))
        elif symbol == "(":
            node = expression(1)
            if tokens[index][0] != ")":
                raise ValueError(f"Позиция {tokens[index][1]}: ожидалась закрывающая скобка")
            index += 1
        else:
            raise ValueError(f"Позиция {position}: ожидалась переменная, отрицание или скобка")

        while PRECEDENCE.get(tokens[index][0], 0) >= minimum:
            operator = tokens[index][0]
            index += 1
            right = expression(PRECEDENCE[operator] + 1)
            node = Formula(operator, (node, right))
        return node

    try:
        result = expression(1)
    except RecursionError:
        raise ValueError("Слишком большая вложенность формулы") from None
    symbol, position = tokens[index]
    if symbol:
        raise ValueError(f"Позиция {position}: неожиданный символ «{symbol}»")
    return result
