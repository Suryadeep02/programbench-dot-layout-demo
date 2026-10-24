"""Corpus properties fixed before the hidden fixtures are generated."""

from collections import Counter
import hashlib
import unittest

from author.generate_cases import build_cases


FAMILIES = {
    "foundations", "rank", "crossing", "orientation", "geometry", "edge",
    "ports", "subgraphs", "clusters", "cycles", "components", "compound",
}


class CaseGeneratorTests(unittest.TestCase):
    def test_frozen_family_distribution(self):
        cases = build_cases()
        self.assertEqual(len(cases), 120)
        self.assertEqual(Counter(case.family for case in cases), {family: 10 for family in FAMILIES})
        self.assertEqual(Counter(case.input_mode for case in cases), {"stdin": 84, "file": 36})

    def test_inputs_are_unique_bounded_and_offline(self):
        cases = build_cases()
        self.assertEqual(len({case.id for case in cases}), len(cases))
        self.assertEqual(len({hashlib.sha256(case.dot.encode()).hexdigest() for case in cases}), len(cases))
        for case in cases:
            self.assertLessEqual(len(case.dot.encode()), 12 * 1024)
            self.assertIn(case.format, {"plain", "plain-ext"})
            self.assertIn(case.input_mode, {"stdin", "file"})
            self.assertTrue(case.dot.startswith(("digraph ", "graph ", "strict digraph ", "strict graph ")))
            self.assertNotIn("http://", case.dot)
            self.assertNotIn("https://", case.dot)
            self.assertNotIn("image=", case.dot)

    def test_ports_and_compound_cases_are_real(self):
        cases = build_cases()
        ports = [case for case in cases if case.family == "ports"]
        self.assertTrue(all(case.format == "plain-ext" for case in ports))
        self.assertTrue(all("shape=record" in case.dot for case in ports))
        compound = [case for case in cases if case.family == "compound"]
        self.assertTrue(all(len(case.tags) >= 3 for case in compound))

    def test_hard_interactions_are_present(self):
        cases = build_cases()
        by_family = {family: [case for case in cases if case.family == family] for family in FAMILIES}
        self.assertTrue(any("label=<" in case.dot for case in by_family["geometry"]))
        self.assertTrue(any("fontname=" in case.dot for case in by_family["geometry"]))
        self.assertTrue(any("subgraph cluster_inner" in case.dot for case in by_family["clusters"]))
        self.assertTrue(any("headport=" in case.dot for case in by_family["ports"]))
        self.assertTrue(any(r'\"' in case.dot for case in by_family["subgraphs"]))
        self.assertGreaterEqual(max(case.dot.count("->") for case in by_family["crossing"]), 25)

    def test_feature_tags_identify_actual_interactions(self):
        for case in build_cases():
            self.assertEqual("html-label" in case.tags, "label=<<" in case.dot)
            self.assertEqual("nested-cluster" in case.tags, "subgraph cluster_inner" in case.dot)
            self.assertEqual("attribute-port" in case.tags, "headport=" in case.dot)
            self.assertEqual("escaped-quote" in case.tags, r'\"' in case.dot)
            self.assertEqual("dense-crossing" in case.tags, case.family == "crossing" and case.dot.count("->") >= 25)

    def test_generation_is_deterministic(self):
        self.assertEqual(build_cases(), build_cases())


if __name__ == "__main__":
    unittest.main()
