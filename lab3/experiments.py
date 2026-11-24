"""Воспроизводит три эксперимента и записывает полные протоколы в reports/lab3."""
from contextlib import redirect_stdout
from copy import deepcopy
import math

from sugeno import HERE, explain, infer, read_json, validate_config, validate_incidents


def configurations():
    base = read_json(HERE / "config.json")
    product = deepcopy(base)
    product["operations"] = "product"
    bell = deepcopy(base)
    # Обе кривые имеют центр 50 и одинаковые точки половинной высоты.
    bell["memberships"]["impact"]["Medium"] = ["bell", 18 * math.sqrt(2 * math.log(2)), 2, 50]
    tuned = deepcopy(base)
    tuned["memberships"]["impact"]["Low"][2] = 28
    tuned["memberships"]["impact"]["Medium"][2] = 20
    tuned["memberships"]["urgency"]["High"][2] = 6.5
    return {"base": base, "product": product, "bell": bell, "tuned": tuned}


def main():
    out = HERE.parent / "reports" / "lab3"
    out.mkdir(parents=True, exist_ok=True)
    rows = validate_incidents(read_json(HERE / "incidents.json"))
    results = {}
    for name, config in configurations().items():
        validate_config(config)
        results[name] = [infer(row, config) for row in rows]
        with (out / f"{name}.txt").open("w", encoding="utf-8") as file, redirect_stdout(file):
            explain(rows, results[name], config)
    print("| Инцидент | База WA / RMS | Произведение WA / RMS | Bell WA / RMS | Настройка WA / RMS |")
    print("|---|---:|---:|---:|---:|")
    for i, row in enumerate(rows):
        cells = [f"{res[i]['wa']:.3f} / {res[i]['rms']:.3f}" for res in results.values()]
        print("| " + " | ".join([row["id"], *cells]) + " |")


if __name__ == "__main__":
    main()
