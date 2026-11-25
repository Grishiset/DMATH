"""Проверка шагов доказательства в исчислении варианта 4."""
import argparse
import os
from pathlib import Path
import sys
import textwrap

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


class Console:
    """Интерактивный интерфейс, не меняющий правила проверки доказательства."""

    def __init__(self, color=True):
        self.color = color and sys.stdout.isatty() and os.environ.get("TERM") != "dumb" and "NO_COLOR" not in os.environ
        self.proof = Proof()
        self.history = []
        self.rejected = 0

    def paint(self, text, code):
        return f"\033[{code}m{text}\033[0m" if self.color else text

    def heading(self, title):
        print(f"\n{self.paint('━' * 64, '36')}")
        print(self.paint(title, '1;36'))
        print(self.paint('─' * 64, '36'))

    def help(self):
        self.heading("КОМАНДЫ И СИНТАКСИС")
        rows = (
            ("/axioms", "Все 11 схем аксиом"),
            ("/history", "История принятых шагов с обоснованиями"),
            ("/demo", "Доказать p → p в отдельном сеансе"),
            ("/reset", "Начать новое доказательство"),
            ("/help", "Показать эту памятку"),
            ("/exit", "Завершить работу (или пустая строка)"),
        )
        for command, description in rows:
            print(f"  {self.paint(command.ljust(12), '1;36')} {description}")
        print("\n  ->  импликация     !  отрицание     &  И     |  ИЛИ")
        print("  Приоритет: !, &, |, ->. Импликация левоассоциативна.")
        print("  Пример: p -> (q -> p)")

    def submit(self, line):
        try:
            valid, message = self.proof.check(line)
        except (ValueError, RecursionError) as error:
            valid, message = False, f"Ошибка формулы: {error}"
        if valid:
            label, color = "ПРИНЯТО", '1;32'
            if len(self.history) < len(self.proof.steps):
                self.history.append(message)
        else:
            label, color = "ОТКЛОНЕНО", '1;31'
            self.rejected += 1
        print(self.paint(f"  [{label}]", color))
        print(textwrap.fill(message, width=76, initial_indent="  ", subsequent_indent="  "))
        return valid

    def show_history(self):
        self.heading("ИСТОРИЯ ДОКАЗАТЕЛЬСТВА")
        if not self.history:
            print("  Пока нет принятых шагов.")
        for message in self.history:
            print(textwrap.fill(message, width=76, initial_indent="  ", subsequent_indent="    "))
        print(f"\n  Принято уникальных формул: {len(self.proof.steps)} | Отклонено: {self.rejected}")

    def demo(self):
        self.heading("ДЕМОНСТРАЦИЯ · ДОКАЗАТЕЛЬСТВО p → p")
        demo = Console(color=self.color)
        try:
            lines = (Path(__file__).parent / "examples" / "proof.txt").read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError) as error:
            print(self.paint(f"  Не удалось открыть пример: {error}", '31'))
            return
        for line in lines:
            if line.strip():
                print(self.paint(f"  › {line}", '36'))
                demo.submit(line)
        print("\n  Демонстрация завершена. Ваше доказательство сохранено.")

    def run(self):
        self.heading("ЛАБОРАТОРНАЯ № 1  /  ВЕРИФИКАТОР ДОКАЗАТЕЛЬСТВ")
        print("  Дискретная математика · Вариант 4")
        print("  11 схем аксиом   |   Правило Modus Ponens")
        self.help()
        while True:
            print()
            prompt = self.paint(f"[{len(self.proof.steps)} принято] Формула › ", '1;36')
            try:
                line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line or line == "/exit":
                break
            if line == "/help":
                self.help()
            elif line == "/axioms":
                self.heading("СХЕМЫ АКСИОМ · ВАРИАНТ 4")
                for i, schema in enumerate(SCHEMES, 1):
                    print(f"  {self.paint(f'A{i:02}', '1;36')}  {schema}")
            elif line == "/history":
                self.show_history()
            elif line == "/demo":
                self.demo()
            elif line == "/reset":
                self.proof = Proof()
                self.history.clear()
                self.rejected = 0
                print(self.paint("  Новое доказательство начато.", '32'))
            elif line.startswith("/"):
                print("  Неизвестная команда. Введите /help.")
            else:
                self.submit(line)
        self.show_history()
        print(self.paint("  Сеанс завершён.\n", '36'))
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", nargs="?", type=Path, help="файл UTF-8, одна формула на строку")
    parser.add_argument("--no-color", action="store_true", help="отключить цвета в консоли")
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
    return Console(color=not args.no_color).run()


if __name__ == "__main__":
    raise SystemExit(main())
