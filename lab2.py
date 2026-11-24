"""Таблицы истинности, сравнение логик и семантическое следование."""
import argparse
from collections import Counter
from itertools import product

from formula import parse


# Целые числа кодируют удвоенные значения истинности.
DOMAINS = {"C2": (0, 2), "K3": (0, 1, 2), "L3": (0, 1, 2)}
LABEL = ("0", "½", "1")


def evaluate(node, env, logic):
    if not node.args:
        return env[node.symbol]
    a = evaluate(node.args[0], env, logic)
    if node.symbol == "¬":
        return 2 - a
    b = evaluate(node.args[1], env, logic)
    if node.symbol == "∧":
        return min(a, b)
    if node.symbol == "∨":
        return max(a, b)
    if logic == "L3":
        return min(2, 2 - a + b)
    return max(2 - a, b)


def interpretations(formulas, logic):
    names = sorted(set().union(*(f.variables() for f in formulas)))
    for values in product(DOMAINS[logic], repeat=len(names)):
        yield dict(zip(names, values))


def assignment(env):
    return ", ".join(f"{k}={LABEL[v]}" for k, v in env.items())


def analyze(formula, logic):
    counts = Counter()
    examples = {}
    for env in interpretations([formula], logic):
        value = evaluate(formula, env, logic)
        counts[value] += 1
        examples.setdefault(value, env)
    props = (counts[2] == counts.total(), counts[2] > 0, counts[0] == counts.total())
    return counts, props, examples


def consequence(premises, conclusion, logic):
    models = 0
    counterexample = None
    for env in interpretations([*premises, conclusion], logic):
        if all(evaluate(p, env, logic) == 2 for p in premises):
            models += 1
            if evaluate(conclusion, env, logic) != 2 and counterexample is None:
                counterexample = env
    return models, counterexample


def compare(formula, logics, table):
    # K3 и L3 имеют общий универсум, C2 задана только на булевых строках.
    widest = max(logics, key=lambda name: len(DOMAINS[name]))
    names = sorted(formula.variables())
    if table:
        print(" | ".join([*names, *logics]))
    different = None
    for env in interpretations([formula], widest):
        values = {logic: evaluate(formula, env, logic) for logic in logics
                  if all(v in DOMAINS[logic] for v in env.values())}
        if len(set(values.values())) > 1 and different is None:
            different = assignment(env)
        if table:
            print(" | ".join([*(LABEL[env[k]] for k in names),
                              *(LABEL[values[k]] if k in values else "—" for k in logics)]))
    properties = []
    for logic in logics:
        counts, props, examples = analyze(formula, logic)
        properties.append(props)
        print(f"{logic}: строк {counts.total()}, моделей {counts[2]}. "
              f"Общезначима / выполнима / тождественно ложна: "
              + " / ".join("да" if b else "нет" for b in props))
        for value in (0, 1):
            if value in examples:
                print(f"  Контрпример общезначимости: {assignment(examples[value])}, F={LABEL[value]}")
                break
    if len(logics) > 1:
        print("Значения на общих оценках:", f"расходятся при {different}" if different else "совпадают")
        print("Три свойства:", "совпадают" if len(set(properties)) == 1 else "различаются")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("formula", help="исследуемая формула или заключение")
    parser.add_argument("--logic", choices=DOMAINS, help="по умолчанию сравниваются все три логики")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--values", nargs="+", help="оценка, например p=1/2 q=1")
    mode.add_argument("--premises", nargs="*", help="посылки, каждая в отдельных кавычках")
    parser.add_argument("--summary", action="store_true", help="скрыть строки таблицы")
    args = parser.parse_args()
    logics = [args.logic] if args.logic else list(DOMAINS)
    try:
        goal = parse(args.formula)
        if args.premises is not None:
            premises = list(map(parse, args.premises))
            for logic in logics:
                models, witness = consequence(premises, goal, logic)
                if witness is not None:
                    result = f"не следует. {assignment(witness)}, заключение={LABEL[evaluate(goal, witness, logic)]}"
                elif models == 0:
                    result = "следует вакуумно, совместных моделей посылок нет"
                else:
                    result = "следует"
                print(f"{logic}: {result}. Моделей посылок: {models}.")
        elif args.values:
            env = {}
            labels = {"0": 0, "0.5": 1, "1/2": 1, "½": 1, "1": 2}
            for item in args.values:
                name, sep, value = item.partition("=")
                if not sep or name in env or value not in labels:
                    raise ValueError(f"Некорректная оценка {item}")
                env[name] = labels[value]
            if set(env) != goal.variables():
                raise ValueError("Задайте ровно по одной оценке для каждой переменной формулы")
            for logic in logics:
                if all(v in DOMAINS[logic] for v in env.values()):
                    print(f"{logic}: {LABEL[evaluate(goal, env, logic)]}")
                elif args.logic:
                    raise ValueError(f"Оценка вне области {logic}")
                else:
                    print(f"{logic}: оценка вне области")
        else:
            compare(goal, logics, not args.summary)
    except (ValueError, RecursionError) as error:
        parser.exit(2, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()
