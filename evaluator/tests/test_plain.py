"""Adversarial contract tests for the plain-output comparator."""

import unittest

from evaluator.plain import compare_plain


REFERENCE = """graph 1 1 2
node a 0.5 1.75 0.75 0.5 alpha solid ellipse black lightgrey
node b 0.5 0.25 0.75 0.5 beta filled box blue white
edge a b 4 0.5 1.5 0.5 1.3 0.5 0.8 0.5 0.5 link 0.5 1 solid red
stop
"""


def accepted(candidate: str, reference: str = REFERENCE) -> bool:
    return compare_plain(reference, candidate)[0]


class PlainComparatorTests(unittest.TestCase):
    def test_exact_reference_passes(self):
        self.assertTrue(accepted(REFERENCE))

    def test_record_order_and_insignificant_whitespace_pass(self):
        lines = REFERENCE.splitlines()
        candidate = "\n".join([lines[0], "  " + lines[2], lines[3], lines[1], lines[4]]) + "\n"
        self.assertTrue(accepted(candidate))

    def test_semantic_quoting_passes(self):
        self.assertTrue(accepted(REFERENCE.replace("node a ", 'node "a" ', 1)))

    def test_html_like_label_with_attributes_is_one_field(self):
        html = '<<TABLE BORDER="0" CELLBORDER="1"><TR><TD>stage 8</TD></TR></TABLE>>'
        reference = REFERENCE.replace("alpha solid ellipse", f"{html} solid plaintext")
        self.assertTrue(accepted(reference, reference))
        self.assertFalse(accepted(reference.replace("stage 8", "stage 9"), reference))

    def test_small_single_coordinate_drift_passes(self):
        self.assertTrue(accepted(REFERENCE.replace("0.5 1.75", "0.52 1.75", 1)))

    def test_large_single_coordinate_drift_fails(self):
        self.assertFalse(accepted(REFERENCE.replace("0.5 1.75", "0.54 1.75", 1)))

    def test_systematic_small_drift_fails_mean_cap(self):
        candidate = """graph 1.02 1.02 2.02
node a 0.52 1.77 0.77 0.52 alpha solid ellipse black lightgrey
node b 0.52 0.27 0.77 0.52 beta filled box blue white
edge a b 4 0.52 1.52 0.52 1.32 0.52 0.82 0.52 0.52 link 0.52 1.02 solid red
stop
"""
        self.assertFalse(accepted(candidate))

    def test_missing_or_extra_node_fails(self):
        lines = REFERENCE.splitlines()
        self.assertFalse(accepted("\n".join([lines[0], lines[1], lines[3], lines[4]]) + "\n"))
        self.assertFalse(accepted(REFERENCE.replace("stop\n", lines[1] + "\nstop\n")))

    def test_missing_or_duplicate_edge_fails(self):
        line = REFERENCE.splitlines()[3]
        self.assertFalse(accepted(REFERENCE.replace(line + "\n", "")))
        self.assertFalse(accepted(REFERENCE.replace("stop\n", line + "\nstop\n")))

    def test_every_structural_field_is_checked(self):
        mutations = [
            ("graph 1 1 2", "graph 1 1 2.1"),
            ("alpha solid ellipse black lightgrey", "alpha solid box black lightgrey"),
            ("alpha solid ellipse black lightgrey", "wrong solid ellipse black lightgrey"),
            ("alpha solid ellipse black lightgrey", "alpha filled ellipse black lightgrey"),
            ("alpha solid ellipse black lightgrey", "alpha solid ellipse green lightgrey"),
            ("alpha solid ellipse black lightgrey", "alpha solid ellipse black pink"),
            ("edge a b 4", "edge b a 4"),
            ("edge a b 4", "edge a b 3"),
            ("link 0.5 1 solid red", "wrong 0.5 1 solid red"),
            ("link 0.5 1 solid red", "link 0.5 1 dashed red"),
            ("link 0.5 1 solid red", "link 0.5 1 solid blue"),
        ]
        for before, after in mutations:
            with self.subTest(after=after):
                self.assertFalse(accepted(REFERENCE.replace(before, after, 1)))

    def test_ports_are_compared(self):
        port_ref = REFERENCE.replace("edge a b 4", "edge a:out b:in 4")
        self.assertFalse(accepted(REFERENCE, port_ref))
        self.assertTrue(accepted(port_ref, port_ref))

    def test_parallel_edges_are_matched_one_to_one(self):
        second = REFERENCE.splitlines()[3].replace("0.5 1.5", "0.55 1.5", 1)
        two = REFERENCE.replace("stop\n", second + "\nstop\n")
        lines = two.splitlines()
        swapped = "\n".join([*lines[:3], lines[4], lines[3], lines[5]]) + "\n"
        reused = REFERENCE.replace("stop\n", lines[3] + "\nstop\n")
        self.assertTrue(accepted(swapped, two))
        self.assertFalse(accepted(reused, two))

    def test_malformed_and_nonfinite_outputs_fail(self):
        mutations = [
            REFERENCE.replace("0.5 1.75", "nan 1.75", 1),
            REFERENCE.replace("0.5 1.75", "inf 1.75", 1),
            REFERENCE.replace("node a", 'node "a', 1),
            REFERENCE.replace("stop\n", "bogus\nstop\n"),
            REFERENCE + "extra\n",
            REFERENCE.replace("stop\n", ""),
        ]
        for candidate in mutations:
            with self.subTest(candidate=candidate[:60]):
                self.assertFalse(accepted(candidate))


if __name__ == "__main__":
    unittest.main()
