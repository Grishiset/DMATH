"""Система Сугено нулевого порядка для приоритизации инцидентов."""
import argparse
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
TERMS = ("Low", "Medium", "High")
# Внутри пары — И, между парами одного правила — ИЛИ.
RULES = (
    (("Low", "Low"),),
    (("Low", "Medium"),),
    (("Medium", "Low"),),
    (("Medium", "Medium"),),
    (("Low", "High"), ("High", "Low")),
    (("Medium", "High"), ("High", "Medium")),
    (("High", "High"),),
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def number(x):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ValueError(f"Требуется конечное число, получено {x!r}")
    return x


def bounded(x, maximum):
    if not 0 <= number(x) <= maximum:
        raise ValueError(f"{x} вне диапазона [0, {maximum}]")
    return x


def membership(x, spec):
    if not isinstance(spec, list) or not spec:
        raise ValueError("Ожидается список с типом и параметрами функции")
    kind, *params = spec
    for parameter in params:
        number(parameter)
    number(x)
    if kind == "sigmoid" and len(params) == 2:
        slope, center = params
        if slope == 0:
            raise ValueError("Нулевой наклон сигмоиды")
        t = slope * (x - center)
        e = math.exp(-abs(t))
        mu = (1 if t >= 0 else e) / (1 + e)
    elif kind == "gauss" and len(params) == 2:
        center, sigma = params
        if sigma <= 0:
            raise ValueError("Ширина гауссовой функции должна быть положительной")
        d = (x - center) / sigma
        mu = math.exp(-0.5 * d * d)
    elif kind == "bell" and len(params) == 3:
        width, slope, center = params
        if width <= 0 or slope <= 0:
            raise ValueError("Ширина и крутизна bell должны быть положительными")
        d = abs((x - center) / width)
        if d == 0:
            mu = 1.0
        else:
            # Та же формула 1/(1+d**(2*b)), без переполнения степени.
            t = 2 * (slope * math.log(d))
            e = math.exp(-abs(t))
            mu = (e if t >= 0 else 1) / (1 + e)
    else:
        raise ValueError(f"Неизвестная функция или неверное число параметров: {spec}")
    return bounded(mu, 1)


def validate_config(config):
    if not isinstance(config, dict) or config.get("operations") not in ("minmax", "product"):
        raise ValueError("operations должно быть minmax или product")
    conclusions = config.get("conclusions")
    if not isinstance(conclusions, list) or len(conclusions) != len(RULES):
        raise ValueError("Требуется семь заключений правил")
    for z in conclusions:
        bounded(z, 100)
    functions = config.get("memberships")
    for key in ("impact", "urgency"):
        group = functions.get(key) if isinstance(functions, dict) else None
        if not isinstance(group, dict) or set(group) != set(TERMS):
            raise ValueError(f"Для {key} требуются функции Low, Medium, High")
        for spec in group.values():
            membership(0, spec)


def validate_incidents(data):
    rows = data.get("incidents") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError("Ожидается массив incidents")
    seen = set()
    for i, row in enumerate(rows, 1):
        try:
            if not isinstance(row, dict):
                raise ValueError("ожидается объект")
            ident = row.get("id")
            if not isinstance(ident, str) or not ident.strip() or ident in seen:
                raise ValueError("требуется уникальный непустой id")
            seen.add(ident)
            bounded(row.get("impact"), 100)
            bounded(row.get("urgency"), 10)
            if "total" in row or "affected" in row:
                total, affected = row.get("total"), row.get("affected")
                if type(total) is not int or type(affected) is not int or not 0 <= affected <= total or total == 0:
                    raise ValueError("требуется 0 ≤ affected ≤ total при total > 0")
                if not math.isclose(row["impact"], 100 * affected / total):
                    raise ValueError("impact расходится с долей затронутых пользователей")
        except (ValueError, OverflowError) as error:
            raise ValueError(f"Инцидент №{i}: {error}") from error
    return rows


def infer(row, config):
    degrees = {key: {term: membership(row[key], spec) for term, spec in group.items()}
               for key, group in config["memberships"].items() if key in ("impact", "urgency")}
    minmax = config["operations"] == "minmax"
    rules = []
    for branches, z in zip(RULES, config["conclusions"]):
        parts = []
        for impact, urgency in branches:
            a, b = degrees["impact"][impact], degrees["urgency"][urgency]
            parts.append(min(a, b) if minmax else a * b)
        alpha = parts[0]
        if len(parts) == 2:
            a, b = parts
            alpha = max(a, b) if minmax else a + b - a * b
        rules.append((parts, alpha, z, alpha * z, alpha * z * z))
    weight = sum(r[1] for r in rules)
    if weight <= 0:
        raise ValueError(f"{row['id']}: ни одно правило не активно")
    weighted = sum(r[3] for r in rules)
    squares = sum(r[4] for r in rules)
    return dict(degrees=degrees, rules=rules, weight=weight, weighted=weighted, squares=squares,
                wa=weighted / weight, rms=math.sqrt(squares / weight))


def explain(rows, results, config):
    for row, res in zip(rows, results):
        print(f"\n{row['id']}   Impact={row['impact']:.3f}%   Urgency={row['urgency']:.3f}")
        for key, group in res["degrees"].items():
            print(key + "  " + "  ".join(f"{k}={v:.3f}" for k, v in group.items()))
        print("Правило | условие и степени ветвей | α | z | αz | αz²")
        for i, (parts, alpha, z, wa, rms) in enumerate(res["rules"], 1):
            if alpha == 0:
                continue
            conditions = [f"(I.{imp} И U.{urg})={value:.3f}"
                          for (imp, urg), value in zip(RULES[i - 1], parts)]
            print(f"R{i} | {' ИЛИ '.join(conditions)} | {alpha:.3f} | {z:.3f} | {wa:.3f} | {rms:.3f}")
        print(f"Σα={res['weight']:.3f}  Σαz={res['weighted']:.3f}  Σαz²={res['squares']:.3f}")
        print(f"WA={res['wa']:.3f}  RMS={res['rms']:.3f}")
    for method in ("wa", "rms"):
        print(f"\nРейтинг по {method.upper()} ({config['operations']})")
        print("ID | Impact | Urgency | WA | RMS")
        for row, res in sorted(zip(rows, results), key=lambda pair: -pair[1][method]):
            print(f"{row['id']} | {row['impact']:.3f} | {row['urgency']:.3f} | {res['wa']:.3f} | {res['rms']:.3f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=HERE / "incidents.json")
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    args = parser.parse_args()
    try:
        config = read_json(args.config)
        validate_config(config)
        rows = validate_incidents(read_json(args.data))
        results = [infer(row, config) for row in rows]
        explain(rows, results, config)
    except (OSError, ValueError, OverflowError, RecursionError) as error:
        parser.exit(2, f"Ошибка: {error}\n")


if __name__ == "__main__":
    main()
