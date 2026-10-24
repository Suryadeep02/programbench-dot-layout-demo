"""Source-only boundary tests for candidate clean-room builds."""

from pathlib import Path
import tempfile
import unittest

from author.validate_submission import scan_source, suspicious_binary


class SubmissionScanTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "compile.sh").write_text("#!/bin/sh\nmkdir -p build\n", encoding="utf-8")

    def test_text_source_is_accepted(self):
        (self.root / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
        self.assertEqual(scan_source(self.root), [])

    def test_prebuilt_elf_and_archive_are_rejected(self):
        (self.root / "payload").write_bytes(b"\x7fELF" + b"a" * 100)
        self.assertTrue(scan_source(self.root))
        (self.root / "payload").write_bytes(b"PK\x03\x04" + b"a" * 100)
        self.assertTrue(scan_source(self.root))

    def test_encoded_binary_payload_is_rejected(self):
        (self.root / "data.py").write_text("blob = '" + "A" * 1024 + "'\n", encoding="utf-8")
        self.assertTrue(scan_source(self.root))

    def test_missing_build_contract_is_rejected(self):
        (self.root / "compile.sh").unlink()
        self.assertTrue(scan_source(self.root))

    def test_symlink_is_rejected(self):
        target = self.root / "main.c"
        target.write_text("int main(void) { return 0; }", encoding="utf-8")
        link = self.root / "source-link.c"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlink creation unavailable")
        self.assertTrue(scan_source(self.root))

    def test_repacked_or_lightly_patched_reference_is_detected(self):
        reference = b"\x7fELF" + bytes(range(256)) * 40
        patched = bytearray(reference)
        for index in range(200, len(patched), 2048):
            patched[index] ^= 1
        self.assertTrue(suspicious_binary(reference, reference))
        self.assertTrue(suspicious_binary(reference, b"preamble" + reference))
        self.assertTrue(suspicious_binary(reference, bytes(patched)))
        self.assertFalse(suspicious_binary(reference, b"\x7fELF" + bytes(reversed(range(256))) * 40))


if __name__ == "__main__":
    unittest.main()
