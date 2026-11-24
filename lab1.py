"""Проверка шагов доказательства в исчислении варианта 4."""
import argparse
from pathlib import Path

from formula import Formula, parse


SCHEMES = tuple(map(parse, (
    "p -> (q -> p)",
    "(s -> (p -> q)) -> ((s -> p) -> (s -> q))",
    "p & q -> p",
    "p & q -> q",
    "p -> (q -> p & q)",
    "p -> p | q",
    "q -> p | q",
    "(p -> r) -> ((q -> r) -> (p | q -> r))",
    "!p -> (p -> q)",
    "(p -> q) -> ((p -> !q) -> !p)",
    "p | !p",
)))


def matches(pattern, actual, bindings):
    if not pattern.args:
        return bindings.setdefault(pattern.symbol, actual) == actual
    return pattern.symbol == actual.symbol and all(
        matches(a, b, bindings) for a, b in zip(pattern.args, actual.args)
    )


def axiom(formula):
    for number, scheme in enumerate(SCHEMES, 1):
        bindings = {}
        if matches(scheme, formula, bindings):
            detail = ", ".join(f"{name} ↦ {value}" for name, value in bindings.items())
            return f"A{number} [{detail}]"
    return None


class Proof:
    def __init__(self):
        self.steps = {}

    def reason(self, goal):
        instance = axiom(goal)
        if instance:
            return f"экземпляр {instance}"
        if goal in self.steps:
            return f"повтор шага {self.steps[goal]}"
        for implication, step in self.steps.items():
            if implication.symbol != "→" or implication.args[1] != goal:
                continue
            premise = implication.args[0]
            source = (f"шаг {self.steps[premise]}" if premise in self.steps else axiom(premise))
            if source:
                return f"MP: {implication} (шаг {step}) и {premise} ({source})"
        # Большая посылка тоже может быть непосредственно экземпляром аксиомы.
        for premise, step in self.steps.items():
            implication = Formula("→", (premise, goal))
            source = axiom(implication)
            if source:
                return f"MP: {implication} ({source}) и {premise} (шаг {step})"
        return None

    def check(self, source):
        formula = parse(source)
        reason = self.reason(formula)
        if reason is None:
            return False, f"Отклонено: для {formula} нет обоснования на этом шаге."
        number = self.steps.setdefault(formula, len(self.steps) + 1)
        return True, f"Шаг {number}. Принято {formula} — {reason}."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, help="файл UTF-8, одна формула на строку")
    args = parser.parse_args()
    proof = Proof()

    def submit(line):
        try:
            valid, message = proof.check(line)
            print(message)
            return valid
        except (ValueError, RecursionError) as error:
            print(f"Ошибка формулы: {error}")
            return False

    if args.file:
        try:
            lines = args.file.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError) as error:
            parser.exit(2, f"{error}\n")
        success = True
        for line in lines:
            if line.strip():
                success = submit(line) and success
        return int(not success)
    print("Вариант 4. Вводите по одной формуле. Пустая строка завершает сеанс.")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if not line.strip():
            break
        submit(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
