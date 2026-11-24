"""Регрессии по методичке и замечаниям к защите. Запуск: python -m unittest -v"""
import math
import unittest
from copy import deepcopy

from formula import parse
from lab1 import Proof, SCHEMES, axiom
from lab2 import DOMAINS, analyze, consequence, evaluate
from lab2_variant import FORMULAS, RELATIONS
from lab3.sugeno import HERE, infer, membership, read_json, validate_config, validate_incidents


class SyntaxTests(unittest.TestCase):
    def test_parser_and_parentheses(self):
        self.assertEqual(parse("(((a) → b)) → (f → ((p → (q))))"), parse("(a->b)->(f->(p->q))"))
        for bad in ("p → (p → p))", "mn → (p → p)", "q → (p p)", "→ a → b", "a → b →",
                    "", "()", "A", "x+y", "(q"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse(bad)

    def test_associativity_and_precedence(self):
        self.assertEqual(parse("a ⊃ b -> c"), parse("(a -> b) → c"))
        self.assertNotEqual(parse("a -> b -> c"), parse("a -> (b -> c)"))
        self.assertEqual(parse("!p&q|r->s"), parse("(((¬p)∧q)∨r)→s"))


class ProofTests(unittest.TestCase):
    def test_all_eleven_axioms_and_implicit_mp_premises(self):
        self.assertEqual(len(SCHEMES), 11)
        for i, schema in enumerate(SCHEMES, 1):
            with self.subTest(axiom=i):
                self.assertTrue(axiom(schema).startswith(f"A{i} "))
                # Справа и слева составные подстановки, одна и та же p везде.
                instance = parse(str(schema).replace("p", "(a ∧ b)").replace("q", "¬c"))
                self.assertTrue(axiom(instance).startswith(f"A{i} "))
                proof = Proof()
                goal = f"x -> {instance}"
                self.assertTrue(proof.check(f"{instance} -> ({goal})")[0])
                accepted, why = proof.check(goal)
                self.assertTrue(accepted)
                self.assertIn("MP", why)
                self.assertIn(f"A{i} ", why)

    def test_proof_and_no_beta_on_previous_theorem(self):
        proof = Proof()
        from pathlib import Path
        path = Path(__file__).parent / "examples" / "proof.txt"
        for step in path.read_text(encoding="utf-8").splitlines():
            self.assertTrue(proof.check(step)[0])
        self.assertFalse(proof.check("z -> z")[0])

    def test_refusals_leave_history_intact(self):
        proof = Proof()
        self.assertFalse(proof.check("p -> (q -> r)")[0])
        with self.assertRaises(ValueError):
            proof.check("p -> ")
        self.assertEqual(proof.steps, {})
        self.assertTrue(proof.check("p -> (q -> p)")[0])
        self.assertFalse(proof.check("q -> p")[0])
        self.assertFalse(proof.check("p")[0])
        self.assertEqual(len(proof.steps), 1)

    def test_implicit_major_premise(self):
        proof = Proof()
        proof.check("p | !p")
        ok, reason = proof.check("x -> (p | !p)")
        self.assertTrue(ok)
        self.assertIn("A1 ", reason)


class SemanticsTests(unittest.TestCase):
    def test_all_implication_cells(self):
        f = parse("p -> q")
        for logic, expected in {"C2": [2, 2, 0, 2],
                                "K3": [2, 2, 2, 1, 1, 2, 0, 1, 2],
                                "L3": [2, 2, 2, 1, 2, 2, 0, 1, 2]}.items():
            self.assertEqual([evaluate(f, {"p": p, "q": q}, logic)
                              for p in DOMAINS[logic] for q in DOMAINS[logic]], expected)

    def test_formula_model_counts(self):
        for source, expected in zip(FORMULAS, [(2, 2, 3), (4, 6, 7), (2, 2, 3), (8, 18, 26), (0, 0, 0)]):
            f = parse(source)
            for logic, n in zip(DOMAINS, expected):
                counts, props, _ = analyze(f, logic)
                self.assertEqual(counts[2], n)
                self.assertEqual(counts.total(), len(DOMAINS[logic]) ** len(f.variables()))
                if source == FORMULAS[-1]:
                    self.assertEqual(props, (False, False, logic == "C2"))

    def test_relations_and_counterexamples(self):
        for (sources, source), answers in zip(RELATIONS, [(1, 1, 1), (1, 1, 0), (1, 0, 0), (0, 0, 0)]):
            premises, goal = list(map(parse, sources)), parse(source)
            for logic, expected in zip(DOMAINS, answers):
                models, witness = consequence(premises, goal, logic)
                self.assertGreater(models, 0)
                self.assertEqual(witness is None, bool(expected))
                if witness is not None:
                    self.assertTrue(all(evaluate(f, witness, logic) == 2 for f in premises))
                    self.assertLess(evaluate(goal, witness, logic), 2)

    def test_vacuous_entailment(self):
        for logic in DOMAINS:
            self.assertEqual(consequence([parse("p"), parse("!p")], parse("q"), logic), (0, None))
            self.assertIsNotNone(consequence([], parse("q"), logic)[1])


class SugenoTests(unittest.TestCase):
    def setUp(self):
        self.config = read_json(HERE / "config.json")

    def test_memberships_at_centers_and_half_height(self):
        for x, spec, expected in [(25, ["sigmoid", -.12, 25], .5), (50, ["gauss", 50, 18], 1),
                                  (50 + 18 * math.sqrt(2 * math.log(2)), ["gauss", 50, 18], .5),
                                  (7, ["bell", 2, 2, 5], .5)]:
            self.assertAlmostEqual(membership(x, spec), expected)

    def test_invalid_input(self):
        row = {"id": "test", "impact": 70, "urgency": 3}
        bad = [None, {}, [row, row], [{"id": "x"}]]
        for field, value in (("id", ""), ("impact", 101), ("impact", "1"), ("urgency", -1),
                             ("urgency", True), ("urgency", float("nan")), ("impact", float("inf"))):
            bad.append([{**row, field: value}])
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_incidents({"incidents": rows})

    def test_invalid_parameters(self):
        for spec in (["gauss", 50, 0], ["sigmoid", 0, 25], ["bell", 2, -1, 2], ["bad"]):
            config = deepcopy(self.config)
            config["memberships"]["impact"]["Low"] = spec
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_closed_form_for_composite_rules_and_aggregation(self):
        for group in self.config["memberships"].values():
            for term in group:
                group[term] = ["sigmoid", 1, 0]
        for ops, single, combined in [("minmax", .5, .5), ("product", .25, .4375)]:
            self.config["operations"] = ops
            result = infer({"id": "x", "impact": 0, "urgency": 0}, self.config)
            weights = [single] * 4 + [combined] * 2 + [single]
            z = [0, 25, 30, 50, 57, 82, 100]
            self.assertEqual([r[1] for r in result["rules"]], weights)
            self.assertAlmostEqual(result["wa"], sum(w*v for w, v in zip(weights, z))/sum(weights))
            self.assertAlmostEqual(result["rms"], math.sqrt(sum(w*v*v for w, v in zip(weights, z))/sum(weights)))

    def test_boundaries_and_no_active_rules(self):
        for impact in (0, 100):
            for urgency in (0, 10):
                result = infer({"impact": impact, "urgency": urgency}, self.config)
                self.assertTrue(0 <= result["wa"] <= result["rms"] <= 100)
        for group in self.config["memberships"].values():
            for term in group:
                group[term] = ["gauss", 10000, 1]
        with self.assertRaisesRegex(ValueError, "ни одно правило"):
            infer({"id": "zero", "impact": 0, "urgency": 0}, self.config)


if __name__ == "__main__":
    unittest.main()
