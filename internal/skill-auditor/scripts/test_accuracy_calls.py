"""Tests for accuracy_review.py real runs: a fake CLAUDE binary answers the batched calls."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from common import AUDITOR_ROOT
from test_accuracy_releases import git
from test_accuracy_review import REGISTRY, SCRIPT

FIXTURES = AUDITOR_ROOT / "fixtures" / "accuracy-calls"
FAKE = FIXTURES / "fake_claude.py"
NOTES = "docs/sdks/ios/release-notes.md"
OLD_NOTES = "# Release notes\n\n## 9.8.0\n\n### New Features\n\n#### Barcode\n\n* Older item.\n"
NEW_NOTES = OLD_NOTES + """
## 9.9.0

### Deprecations

#### Barcode

* `BarcodeCaptureOverlayStyle.legacy` is deprecated. Use `.frame`.

### New Features

#### Barcode

* Added `BarcodeCapture.feedback`.

#### Core

* Core item.

#### Id

* Id item.

#### Label

* Label item without a mapped skill.
"""
SKILL_PATH = "barcode-capture-ios/SKILL.md"
BARCODE_IDS = ("ios/9.9.0/1", "ios/9.9.0/2")
CORE_ID, ID_ID, LABEL_ID = "ios/9.9.0/3", "ios/9.9.0/4", "ios/9.9.0/5"
DEPRECATED_LINE = 11


def reply(*items):
    return {"result": json.dumps({"items": [{"id": i, "findings": f} for i, f in items]})}


def outdated(path=SKILL_PATH, line=DEPRECATED_LINE, quote=".legacy"):
    return {"kind": "outdated", "path": path, "line": line, "quote": quote,
            "why": "deprecated in 9.9.0", "confidence": "high"}


def not_covered(skill="barcode-capture-ios"):
    return {"kind": "not-covered", "skill": skill, "why": "new feedback API", "confidence": "medium"}


GOOD_BARCODE = reply((BARCODE_IDS[0], []), (BARCODE_IDS[1], []))
GOOD_CORE = reply((CORE_ID, []))
GOOD_ID = reply((ID_ID, []))


class CallsFixture(unittest.TestCase):
    """A docs clone with one new iOS release and a fake CLAUDE binary; no tests of its own."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.docs = cls.tmp / "docs-clone"
        (cls.docs / NOTES).parent.mkdir(parents=True)
        git(cls.docs, "init", "-q")
        (cls.docs / NOTES).write_text(OLD_NOTES)
        git(cls.docs, "add", "-A")
        git(cls.docs, "commit", "-q", "-m", "old")
        cls.old = git(cls.docs, "rev-parse", "HEAD")
        (cls.docs / NOTES).write_text(NEW_NOTES)
        git(cls.docs, "add", "-A")
        git(cls.docs, "commit", "-q", "-m", "new")
        data = json.loads(REGISTRY.read_text())
        data["platforms"] = {"ios": {"notes": NOTES, "skills": ["barcode-capture-ios", "id-capture-ios"]}}
        data["not_assessed"] = {}
        cls.registry = cls.tmp / "registry.json"
        cls.registry.write_text(json.dumps(data))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        self.log = self.work / "calls.log"
        self.skills = self.make_skills("outdated")

    def make_skills(self, variant):
        skills = self.work / f"skills-{variant}"
        shutil.copytree(FIXTURES / variant / "barcode-capture-ios", skills / "barcode-capture-ios")
        (skills / "barcode-capture-ios" / "references").mkdir()
        (skills / "barcode-capture-ios" / "references" / "api.md").write_text("# API\n\nSee the overlay.\n")
        (skills / "id-capture-ios").mkdir()
        (skills / "id-capture-ios" / "SKILL.md").write_text("# Id capture\n")
        return skills

    def calls(self):
        return len(self.log.read_text().splitlines()) if self.log.exists() else 0

    def scripted(self, *replies):
        path = self.work / "replies.json"
        path.write_text(json.dumps(replies))
        return {"FAKE_CLAUDE_REPLIES": str(path)}

    def run_script(self, *args, env=None, dry=False):
        full = {**os.environ, "CLAUDE": str(FAKE), "FAKE_CLAUDE_LOG": str(self.log), **(env or {})}
        cmd = [sys.executable, str(SCRIPT), "--docs", str(self.docs), "--skills", str(self.skills),
               "--registry", str(self.registry), "--from", self.old, "--out", str(self.work / "out")]
        if dry:
            cmd.append("--dry-run")
        return subprocess.run([*cmd, *args], capture_output=True, text=True, env=full)

    def run_ok(self, *args, **kwargs):
        proc = self.run_script(*args, **kwargs)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def entries(self, out):
        return {e["id"]: e for r in out["releases"] for p in r["platforms"] for e in p["entries"]}


class AccuracyCallsTest(CallsFixture):
    def test_calls_made_equal_dry_run_planned_calls(self):
        planned = self.run_ok("--max-batch-bytes", "1", dry=True)["releases"][0]["totals"]["planned_calls"]
        out = self.run_ok("--max-batch-bytes", "1", "--max-calls", "100")
        self.assertGreaterEqual(planned, 2)
        self.assertEqual(self.calls(), planned)
        self.assertEqual(out["usage"]["calls"], planned)

    def test_outdated_and_not_covered_findings_parse_onto_their_items(self):
        env = self.scripted(
            reply((BARCODE_IDS[0], [outdated()]), (BARCODE_IDS[1], [not_covered()])), GOOD_CORE, GOOD_ID)
        entries = self.entries(self.run_ok("--max-calls", "10", env=env))
        self.assertEqual(entries[BARCODE_IDS[0]]["findings"], [outdated()])
        self.assertEqual(entries[BARCODE_IDS[1]]["findings"], [not_covered()])
        self.assertEqual(entries[BARCODE_IDS[0]]["outcome"], "finding")
        self.assertEqual(entries[BARCODE_IDS[1]]["outcome"], "finding")

    def test_every_item_ends_with_exactly_one_outcome(self):
        planned = self.entries(self.run_ok(dry=True))
        env = self.scripted(reply((BARCODE_IDS[0], [outdated()]), (BARCODE_IDS[1], [])), GOOD_CORE, GOOD_ID)
        out = self.run_ok("--max-calls", "10", env=env)
        entries = self.entries(out)
        self.assertEqual(set(entries), set(planned))
        self.assertEqual({i: e["outcome"] for i, e in entries.items()}, {
            BARCODE_IDS[0]: "finding", BARCODE_IDS[1]: "no-impact", CORE_ID: "no-impact",
            ID_ID: "no-impact", LABEL_ID: "no-skill"})
        row = out["releases"][0]["platforms"][0]
        self.assertEqual(row["outcomes"], {"finding": 1, "no-impact": 3, "no-skill": 1, "not-checked": 0})

    def assert_barcode_batch_not_checked(self, bad, needle):
        env = self.scripted(bad, bad, GOOD_CORE, GOOD_ID)
        out = self.run_ok("--max-calls", "10", env=env)
        entries = self.entries(out)
        self.assertEqual(self.calls(), 4)
        for item_id in BARCODE_IDS:
            self.assertEqual(entries[item_id]["outcome"], "not-checked")
            self.assertIn(needle, entries[item_id]["reason"])
        self.assertEqual(entries[CORE_ID]["outcome"], "no-impact")
        self.assertEqual(entries[ID_ID]["outcome"], "no-impact")

    def test_missing_item_id_fails_batch_and_is_retried_once(self):
        self.assert_barcode_batch_not_checked(reply((BARCODE_IDS[0], [])), "missing item ids")

    def test_duplicate_item_id_fails_batch_and_is_retried_once(self):
        self.assert_barcode_batch_not_checked(
            reply((BARCODE_IDS[0], []), (BARCODE_IDS[0], []), (BARCODE_IDS[1], [])), "duplicate item id")

    def test_unknown_item_id_fails_batch_and_is_retried_once(self):
        self.assert_barcode_batch_not_checked(
            reply((BARCODE_IDS[0], []), (BARCODE_IDS[1], []), ("ios/9.9.0/99", [])), "unknown item id")

    def test_quote_not_at_the_cited_line_fails_batch_and_is_retried_once(self):
        self.assert_barcode_batch_not_checked(
            reply((BARCODE_IDS[0], [outdated(line=DEPRECATED_LINE + 1)]), (BARCODE_IDS[1], [])), "not found at")

    def test_failed_call_is_retried_once_then_not_checked(self):
        self.assert_barcode_batch_not_checked({"exit": 1}, "call failed")

    def test_retry_can_succeed(self):
        env = self.scripted({"result": "not json"}, GOOD_BARCODE, GOOD_CORE, GOOD_ID)
        entries = self.entries(self.run_ok("--max-calls", "10", env=env))
        self.assertEqual(self.calls(), 4)
        self.assertEqual(entries[BARCODE_IDS[0]]["outcome"], "no-impact")

    def test_reply_wrapped_in_a_json_fence_parses(self):
        fenced = {"result": "```json\n" + GOOD_BARCODE["result"] + "\n```"}
        env = self.scripted(fenced, GOOD_CORE, GOOD_ID)
        self.run_ok("--max-calls", "10", env=env)
        self.assertEqual(self.calls(), 3)

    def outcomes(self, out):
        return {i: (e["outcome"], e.get("reason")) for i, e in self.entries(out).items()}

    def test_run_without_max_calls_exits_2_and_makes_no_call(self):
        proc = self.run_script()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--max-calls", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(self.calls(), 0)

    def test_max_calls_stops_the_run_and_marks_remaining_batches_not_checked(self):
        out = self.run_ok("--max-batch-bytes", "1", "--max-calls", "2")
        self.assertEqual(self.calls(), 2)
        outcomes = self.outcomes(out)
        self.assertEqual(outcomes[CORE_ID], ("not-checked", "limit: max-calls"))
        self.assertEqual(outcomes[ID_ID], ("not-checked", "limit: max-calls"))
        self.assertEqual(outcomes[BARCODE_IDS[0]], ("no-impact", None))

    def test_retry_counts_against_max_calls(self):
        env = self.scripted({"result": "not json"})
        out = self.run_ok("--max-calls", "1", env=env)
        self.assertEqual(self.calls(), 1)
        self.assertEqual(self.outcomes(out)[BARCODE_IDS[0]], ("not-checked", "limit: max-calls"))

    def test_max_input_tokens_is_checked_before_every_call(self):
        out = self.run_ok("--max-calls", "10", "--max-input-tokens", "1500", env={"FAKE_CLAUDE_TOKENS": "1400"})
        self.assertEqual(self.calls(), 1)
        self.assertEqual(out["usage"]["input_tokens"], 1400)
        self.assertEqual(self.outcomes(out)[CORE_ID], ("not-checked", "limit: max-input-tokens"))

    def test_max_cost_usd_is_checked_before_every_call(self):
        out = self.run_ok("--max-calls", "10", "--max-cost-usd", "0.5", env={"FAKE_CLAUDE_COST": "0.5"})
        self.assertEqual(self.calls(), 1)
        self.assertEqual(out["usage"]["cost_usd"], 0.5)
        self.assertEqual(self.outcomes(out)[ID_ID], ("not-checked", "limit: max-cost-usd"))

    def test_missing_claude_binary_exits_2(self):
        proc = self.run_script("--max-calls", "10", env={"CLAUDE": str(self.work / "nope")})
        self.assertEqual(proc.returncode, 2)
        self.assertIn("CLAUDE", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_each_malformed_finding_fails_the_batch(self):
        cases = [
            (outdated(line=999), "not found at"),
            (outdated(quote="nonexistent text"), "not found at"),
            (outdated(quote=""), "not found at"),
            (outdated(line=True, quote="#"), "not found at"),
            (outdated(path="id-capture-ios/SKILL.md", line=1, quote="Id"), "is not a file of this batch"),
            ({**not_covered(), "kind": "weird"}, "unknown finding kind"),
            ({**not_covered(), "confidence": "certain"}, "bad finding"),
            ("oops", "bad finding"),
        ]
        for finding, needle in cases:
            with self.subTest(finding=finding):
                self.log.unlink(missing_ok=True)
                self.assert_barcode_batch_not_checked(reply((BARCODE_IDS[0], [finding]), (BARCODE_IDS[1], [])), needle)

    def test_reply_without_items_list_fails_the_batch(self):
        self.assert_barcode_batch_not_checked({"result": json.dumps({"items": "x"})}, "no 'items' list")

    def test_non_positive_max_input_tokens_or_cost_exits_2(self):
        for flag in ("--max-input-tokens", "--max-cost-usd"):
            with self.subTest(flag=flag):
                proc = self.run_script("--max-calls", "5", flag, "0")
                self.assertEqual((proc.returncode, self.calls()), (2, 0))
                self.assertIn("finite and positive", proc.stderr)

    def test_real_run_without_from_exits_2(self):
        cmd = [sys.executable, str(SCRIPT), "--docs", str(self.docs), "--skills", str(self.skills),
               "--registry", str(self.registry), "--max-calls", "5"]
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              env={**os.environ, "CLAUDE": str(FAKE), "FAKE_CLAUDE_LOG": str(self.log)})
        self.assertEqual((proc.returncode, self.calls()), (2, 0))
        self.assertIn("--from", proc.stderr)

    def test_claude_nonzero_exit_is_reported_as_call_failed(self):
        out = self.run_ok("--max-calls", "10", env=self.scripted({"exit": 3}, {"exit": 3}, GOOD_CORE, GOOD_ID))
        outcome, reason = self.outcomes(out)[BARCODE_IDS[0]]
        self.assertEqual(outcome, "not-checked")
        self.assertIn("call failed: exit 3", reason)

    def test_seeded_pair_outdated_skill_gets_a_finding_and_corrected_skill_none(self):
        env = {"FAKE_CLAUDE_MARKER": "style: .legacy"}
        out = self.run_ok("--max-calls", "10", env=env)
        first = self.entries(out)[BARCODE_IDS[0]]
        self.assertEqual(first["outcome"], "finding")
        self.assertEqual((first["findings"][0]["path"], first["findings"][0]["line"]),
                         (SKILL_PATH, DEPRECATED_LINE))
        self.skills = self.make_skills("corrected")
        out = self.run_ok("--max-calls", "10", env=env)
        self.assertEqual(self.entries(out)[BARCODE_IDS[0]]["outcome"], "no-impact")

    def test_non_positive_max_calls_exits_2(self):
        proc = self.run_script("--max-calls", "-1")
        self.assertEqual((proc.returncode, self.calls()), (2, 0))
        self.assertIn("--max-calls", proc.stderr)

    def test_not_covered_with_a_non_string_skill_fails_the_batch(self):
        bad = reply((BARCODE_IDS[0], [{**not_covered(), "skill": ["barcode-capture-ios"]}]), (BARCODE_IDS[1], []))
        self.assert_barcode_batch_not_checked(bad, "is not in this batch")

    def test_symlink_leaving_the_skill_dir_is_not_sent(self):
        planned = self.run_ok(dry=True)["releases"][0]["totals"]["input_bytes"]
        secret = self.work / "secret.txt"
        secret.write_text("x" * 5000)
        (self.skills / "id-capture-ios" / "leak.md").symlink_to(secret)
        self.assertEqual(self.run_ok(dry=True)["releases"][0]["totals"]["input_bytes"], planned)

    def test_hidden_files_are_not_sent(self):
        planned = self.run_ok(dry=True)["releases"][0]["totals"]["input_bytes"]
        (self.skills / "id-capture-ios" / ".env").write_text("x" * 5000)
        (self.skills / "id-capture-ios" / ".scratch").mkdir()
        (self.skills / "id-capture-ios" / ".scratch" / "notes.md").write_text("x" * 5000)
        self.assertEqual(self.run_ok(dry=True)["releases"][0]["totals"]["input_bytes"], planned)

    def test_visible_symlink_to_a_hidden_file_is_not_sent(self):
        planned = self.run_ok(dry=True)["releases"][0]["totals"]["input_bytes"]
        (self.skills / "id-capture-ios" / ".env").write_text("x" * 5000)
        (self.skills / "id-capture-ios" / "config.txt").symlink_to(".env")
        self.assertEqual(self.run_ok(dry=True)["releases"][0]["totals"]["input_bytes"], planned)

    def test_dry_run_prompt_tokens_is_the_limit_the_real_run_needs(self):
        need = self.run_ok(dry=True)["releases"][0]["totals"]["prompt_tokens"]
        env = self.scripted(*({**r, "usage": {}} for r in (GOOD_BARCODE, GOOD_CORE, GOOD_ID)))
        self.run_ok("--max-calls", "10", "--max-input-tokens", str(need), env=env)
        self.assertEqual(self.calls(), 3)
        self.log.unlink()
        self.run_ok("--max-calls", "10", "--max-input-tokens", str(need - 1), env=env)
        self.assertEqual(self.calls(), 2)

    def test_success_without_a_cost_report_stops_a_cost_limited_run(self):
        for cost in (None, "__absent__"):
            with self.subTest(cost=cost):
                self.log.unlink(missing_ok=True)
                good = {**GOOD_BARCODE, "cost": cost}
                out = self.run_ok("--max-calls", "10", "--max-cost-usd", "0.5", env=self.scripted(good))
                self.assertEqual((self.calls(), out["usage"]["unknown_cost_calls"]), (1, 1))

    def test_non_finite_max_cost_exits_2(self):
        for value in ("nan", "inf"):
            with self.subTest(value=value):
                proc = self.run_script("--max-calls", "5", "--max-cost-usd", value)
                self.assertEqual((proc.returncode, self.calls()), (2, 0))
                self.assertIn("finite and positive", proc.stderr)

    def test_failed_call_without_a_cost_report_stops_a_cost_limited_run(self):
        out = self.run_ok("--max-calls", "10", "--max-cost-usd", "5", env=self.scripted({"exit": 1}))
        self.assertEqual((self.calls(), out["usage"]["unknown_cost_calls"]), (1, 1))

    def test_non_finite_or_negative_usage_fails_the_batch(self):
        for bad in ({**GOOD_BARCODE, "usage": {"input_tokens": 1e999}}, {**GOOD_BARCODE, "cost": -1}):
            with self.subTest(bad=bad):
                self.log.unlink(missing_ok=True)
                self.assert_barcode_batch_not_checked(bad, "invalid reply")

    def test_mapped_skill_without_files_is_not_checked(self):
        (self.skills / "id-capture-ios" / "SKILL.md").unlink()
        out = self.run_ok("--max-calls", "10", env=self.scripted(GOOD_BARCODE, GOOD_CORE))
        self.assertEqual(self.outcomes(out)[ID_ID], ("not-checked", "no skill files: id-capture-ios"))
        self.assertEqual(self.calls(), 2)

    def test_unreadable_skill_file_exits_2_before_any_call(self):
        (self.skills / "id-capture-ios" / "SKILL.md").chmod(0)
        proc = self.run_script("--max-calls", "10")
        self.assertEqual((proc.returncode, self.calls()), (2, 0))
        self.assertIn("cannot read skill file", proc.stderr)

    def test_skill_dir_linking_outside_the_skills_tree_exits_2(self):
        outside = self.work / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text("secret\n")
        shutil.rmtree(self.skills / "id-capture-ios")
        (self.skills / "id-capture-ios").symlink_to(outside)
        proc = self.run_script(dry=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("resolves outside", proc.stderr)

    def test_not_covered_on_a_skill_split_across_batches_is_dropped_and_marked_incomplete(self):
        split = reply((BARCODE_IDS[0], [not_covered()]), (BARCODE_IDS[1], []))
        env = self.scripted(split, GOOD_BARCODE, GOOD_CORE, GOOD_CORE, GOOD_CORE, GOOD_ID)
        entry = self.entries(self.run_ok("--max-batch-bytes", "1", "--max-calls", "10", env=env))[BARCODE_IDS[0]]
        self.assertEqual((entry["outcome"], entry["findings"]), ("no-impact", []))
        self.assertIn("split across batches: barcode-capture-ios", entry["incomplete"])

    def test_timed_out_call_stops_a_cost_limited_run(self):
        env = self.scripted({"sleep": 5})
        out = self.run_ok("--max-calls", "10", "--max-cost-usd", "5", "--timeout", "1", env=env)
        self.assertEqual(self.calls(), 1)
        self.assertEqual(out["usage"]["unknown_cost_calls"], 1)
        self.assertEqual(self.outcomes(out)[CORE_ID], ("not-checked", "limit: max-cost-usd (a call's spend is unknown)"))

    def test_malformed_usage_or_cost_fails_the_batch(self):
        for bad in ({**GOOD_BARCODE, "usage": {"input_tokens": "100"}}, {**GOOD_BARCODE, "cost": "free"}):
            with self.subTest(bad=bad):
                self.log.unlink(missing_ok=True)
                self.assert_barcode_batch_not_checked(bad, "invalid reply")

    def test_finding_survives_a_later_failed_batch_of_the_same_item(self):
        first = reply((BARCODE_IDS[0], [outdated()]), (BARCODE_IDS[1], []))
        bad = {"result": "not json"}
        env = self.scripted(first, bad, bad, GOOD_CORE, GOOD_CORE, GOOD_CORE, GOOD_ID)
        entry = self.entries(self.run_ok("--max-batch-bytes", "1", "--max-calls", "10", env=env))[BARCODE_IDS[0]]
        self.assertEqual(entry["outcome"], "finding")
        self.assertIn("invalid reply", entry["incomplete"])


if __name__ == "__main__":
    unittest.main()
