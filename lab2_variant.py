"""Печать полного протокола проверок варианта 4 (ЛР 2)."""
from formula import parse
from lab2 import DOMAINS, LABEL, assignment, compare, consequence, evaluate

FORMULAS = (
    "p → p",
    "(p ∨ ¬p) → (q ∨ ¬q)",
    "(p ∨ q) → (p ∧ q)",
    "(p → (q → r)) → ((p → q) → (p → r))",
    "(p ∧ ¬p) ∨ (q ∧ ¬q)",
)
RELATIONS = (
    (("p", "p → (q ∨ r)", "q → s", "r → t", "(s ∨ t) → u", "u → v"), "u"),
    (("p → (q ∧ r)", "q → s", "r → t", "(s ∧ t) → u", "u → v"), "¬p ∨ u"),
    (( "(p ∧ q) ∨ r", "p → s", "r → s", "s → t", "t → u"), "u ∧ (q ∨ ¬q)"),
    (("p ∨ q", "p → r", "q → s", "(r ∧ s) → t", "t → u"), "u"),
)


def main():
    for number, source in enumerate(FORMULAS, 1):
        print(f"\nF{number} = {source}")
        compare(parse(source), list(DOMAINS), True)
    for number, (sources, conclusion) in enumerate(RELATIONS, 1):
        print(f"\nR{number}: {', '.join(sources)} ⊨ {conclusion}")
        premises = list(map(parse, sources))
        goal = parse(conclusion)
        for logic in DOMAINS:
            models, witness = consequence(premises, goal, logic)
            verdict = "следует" if witness is None else "не следует"
            print(f"{logic}: {verdict}, совместных моделей посылок {models}")
            if witness is not None:
                print(f"  {assignment(witness)}. Все посылки = 1, заключение = {LABEL[evaluate(goal, witness, logic)]}")


if __name__ == "__main__":
    main()
