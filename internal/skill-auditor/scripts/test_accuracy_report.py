"""Tests for accuracy_review.py --out: report.json, report.md and digest.md written for a canned run."""
import json
import os
import unittest
from pathlib import Path
from unittest import mock

import accuracy_review
import test_accuracy_calls as fixture
from test_accuracy_calls import BARCODE_IDS, CORE_ID, ID_ID, LABEL_ID, not_covered, outdated, reply

ALL_IDS = [*BARCODE_IDS, CORE_ID, ID_ID, LABEL_ID]
MARKER = {"FAKE_CLAUDE_MARKER": ".legacy"}


class AccuracyReportTest(fixture.CallsFixture):
    def out(self, name):
        return self.work / "out" / name

    def report(self):
        return json.loads(self.out("report.json").read_text())

    def ios(self):
        (release,) = self.report()["releases"]
        (row,) = release["platforms"]
        return row

    def test_real_run_lists_every_item_once_in_report_json_and_report_md(self):
        self.run_ok("--max-calls", "10", env=MARKER)
        row = self.ios()
        listed = [i["id"] for i in row["findings"] + row["no_skill"] + row["not_checked"]] + row["no_impact"]
        self.assertEqual(sorted(listed), ALL_IDS)
        self.assertEqual([i["id"] for i in row["findings"]], [BARCODE_IDS[0], CORE_ID])
        self.assertEqual(row["findings"][0]["findings"][0]["path"], fixture.SKILL_PATH)
        self.assertEqual([i["id"] for i in row["no_skill"]], [LABEL_ID])
        self.assertIn(BARCODE_IDS[0], self.out("report.md").read_text())

    def test_max_calls_stop_shows_partial_coverage_per_platform(self):
        self.run_ok("--max-batch-bytes", "1", "--max-calls", "2")
        self.assertEqual(self.ios()["coverage"], {"kept": 5, "checked": 2, "complete": False})
        self.assertEqual({i["id"] for i in self.ios()["not_checked"]}, {CORE_ID, ID_ID})

    def test_complete_run_has_complete_coverage(self):
        self.run_ok("--max-calls", "10")
        self.assertEqual(self.ios()["coverage"], {"kept": 5, "checked": 4, "complete": True})

    def test_cost_label_is_actual_with_an_api_key(self):
        self.run_ok("--max-calls", "10", env={"ANTHROPIC_API_KEY": "dummy", "FAKE_CLAUDE_COST": "0.25"})
        usage = self.report()["usage"]
        self.assertEqual((usage["calls"], usage["cost_label"], usage["cost_usd"]), (3, "actual", 0.75))

    def test_skill_split_across_batches_is_partly_checked_not_complete(self):
        self.run_ok("--max-batch-bytes", "1", "--max-calls", "100")
        self.assertFalse(self.ios()["coverage"]["complete"])
        self.assertEqual({i["id"] for i in self.ios()["partial"]}, {*BARCODE_IDS, CORE_ID})

    def test_cost_label_is_unavailable_when_a_call_reports_no_cost(self):
        env = self.scripted(*({**r, "cost": "__absent__"} for r in (fixture.GOOD_BARCODE, fixture.GOOD_CORE,
                                                                    fixture.GOOD_ID)))
        self.run_ok("--max-calls", "10", env={**env, "ANTHROPIC_API_KEY": "dummy"})
        usage = self.report()["usage"]
        self.assertEqual((usage["cost_label"], usage["cost_usd"], usage["unknown_cost_calls"]),
                         ("unavailable", None, 3))

    def test_out_path_that_is_a_file_exits_2_before_any_call(self):
        (self.work / "out").write_text("not a dir")
        proc = self.run_script("--max-calls", "10")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--out", proc.stderr)
        self.assertEqual(self.calls(), 0)

    def test_report_write_failure_still_prints_the_results(self):
        self.out("").mkdir(0o500)
        self.addCleanup(self.out("").chmod, 0o700)
        proc = self.run_script("--max-calls", "10")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("cannot write reports", proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["usage"]["calls"], self.calls())

    def test_cost_label_is_unavailable_without_an_api_key(self):
        self.run_ok("--max-calls", "10", env={"ANTHROPIC_API_KEY": "", "FAKE_CLAUDE_COST": "0.25"})
        usage = self.report()["usage"]
        self.assertEqual((usage["cost_label"], usage["cost_usd"]), ("unavailable", None))

    def test_dry_run_estimates_cost_and_marks_every_mapped_item_not_checked(self):
        planned = self.run_ok(dry=True)["releases"][0]["totals"]
        usage = self.report()["usage"]
        self.assertEqual(usage["cost_label"], "estimated")
        self.assertEqual((usage["calls"], usage["input_tokens"]), (3, planned["prompt_tokens"]))
        self.assertAlmostEqual(usage["cost_usd"], planned["prompt_tokens"] * 3 / 1_000_000)
        self.assertEqual(self.ios()["coverage"], {"kept": 5, "checked": 0, "complete": False})
        self.assertEqual({i["reason"] for i in self.ios()["not_checked"]}, {"dry run"})

    def test_dry_run_with_an_unpriced_model_has_no_cost(self):
        self.run_ok("--model", "mystery", dry=True)
        usage = self.report()["usage"]
        self.assertEqual((usage["cost_label"], usage["cost_usd"]), ("unavailable", None))

    def test_digest_is_slack_mrkdwn_with_findings_before_counts(self):
        self.run_ok("--max-calls", "10", env=MARKER)
        self.assertEqual(self.out("digest.md").read_text(), (
            "*Release 9.9.0*\n"
            "*ios*\n"
            "• `barcode-capture-ios/SKILL.md:11` (high) “.legacy” — deprecated in this release"
            " [ios/9.9.0/1]\n"
            "• `barcode-capture-ios/SKILL.md:11` (high) “.legacy” — deprecated in this release"
            " [ios/9.9.0/3]\n"
            "No skill: 1 · Not checked: 0\n"))

    def test_digest_escapes_slack_control_characters(self):
        (self.skills / "barcode-capture-ios" / "references" / "api.md").write_text("Use <Overlay> & frame.\n")
        self.run_ok("--max-calls", "10", env={"FAKE_CLAUDE_MARKER": "<Overlay> & frame"})
        digest = self.out("digest.md").read_text()
        self.assertIn("“&lt;Overlay&gt; &amp; frame”", digest)
        self.assertNotIn("<", digest)

    def test_digest_counts_line_flags_an_incomplete_platform(self):
        self.run_ok("--max-batch-bytes", "1", "--max-calls", "2")
        lines = self.out("digest.md").read_text().splitlines()
        self.assertEqual(lines[-1], "No skill: 1 · Not checked: 2 · ios checked 2 of 5, partly checked 2")

    def test_digest_counts_line_flags_partly_checked_items(self):
        self.run_ok("--max-batch-bytes", "1", "--max-calls", "100")
        lines = self.out("digest.md").read_text().splitlines()
        self.assertEqual(lines[-1], "No skill: 1 · Not checked: 0 · ios checked 4 of 5, partly checked 3")

    def test_platform_with_no_mapped_items_is_not_called_complete(self):
        row = {"key": "titanium", "entries": [
            {"id": "titanium/9.9.0/1", "section": "Added", "product": "barcode", "text": "x", "skills": []}]}
        report = {"from": "a", "to": "b", "missing_notes": [], "usage": accuracy_review.usage_block({"releases": []}, None, "x"),
                  "releases": [{"version": "9.9.0", "platforms": [accuracy_review.platform_report(row)]}]}
        self.assertIn("Checked 0 of 1 items (no mapped items).", accuracy_review.render_markdown(report))

    def test_failed_write_keeps_the_previous_report_set(self):
        self.run_ok("--max-calls", "10")
        before = {name: self.out(name).read_text() for name in ("report.json", "report.md", "digest.md")}
        self.out("").chmod(0o500)
        self.addCleanup(self.out("").chmod, 0o700)
        proc = self.run_script("--max-calls", "10", "--to", self.old)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual({name: self.out(name).read_text() for name in before}, before)

    def test_staging_does_not_follow_a_symlink_in_the_out_dir(self):
        victim = self.work / "victim.txt"
        victim.write_text("keep")
        self.out("").mkdir(parents=True)
        os.symlink(victim, self.out("report.json.tmp"))
        self.run_ok("--max-calls", "10")
        self.assertEqual(victim.read_text(), "keep")
        self.assertIn("releases", self.report())

    def test_no_new_release_has_no_digest_and_removes_a_stale_one(self):
        self.run_ok("--max-calls", "10")
        self.assertTrue(self.out("digest.md").exists())
        self.run_ok("--max-calls", "10", "--to", self.old)
        self.assertFalse(self.out("digest.md").exists())
        self.assertEqual(self.report()["releases"], [])

    def test_failed_publish_after_staging_restores_the_previous_report_set(self):
        self.run_ok("--max-calls", "10")
        names = ("report.json", "report.md", "digest.md")
        before = {name: self.out(name).read_bytes() for name in names}
        report = {**self.report(), "releases": []}
        real_replace = Path.replace

        def flaky(src, dst):
            if src.name == "report.md" and src.parent.name.startswith(".staging-"):
                raise OSError("disk full")
            return real_replace(src, dst)

        with mock.patch.object(Path, "replace", autospec=True, side_effect=flaky):
            with self.assertRaises(accuracy_review.UsageError):
                accuracy_review.write_reports(self.out(""), report)
        self.assertEqual({name: self.out(name).read_bytes() for name in names}, before)
        self.assertEqual(sorted(p.name for p in self.out("").iterdir()), sorted(names))

    def test_lone_surrogate_in_a_finding_still_writes_every_report(self):
        bad = {**outdated(), "why": "broken \ud800 text"}
        env = self.scripted(reply((BARCODE_IDS[0], [bad]), (BARCODE_IDS[1], [])), fixture.GOOD_CORE, fixture.GOOD_ID)
        self.run_ok("--max-calls", "10", env=env)
        self.assertEqual(self.ios()["findings"][0]["findings"][0]["why"], "broken \ud800 text")
        self.assertIn("broken \\ud800 text", self.out("report.md").read_text())
        self.assertIn("broken \\ud800 text", self.out("digest.md").read_text())

    def test_report_md_keeps_the_exact_quote_and_the_finding_kind(self):
        quote = "Use `Scanner`  with a frame."
        (self.skills / "barcode-capture-ios" / "references" / "api.md").write_text(quote + "\n")
        found = outdated(path="barcode-capture-ios/references/api.md", line=1, quote=quote)
        env = self.scripted(reply((BARCODE_IDS[0], [found]), (BARCODE_IDS[1], [not_covered()])),
                            fixture.GOOD_CORE, fixture.GOOD_ID)
        self.run_ok("--max-calls", "10", env=env)
        md = self.out("report.md").read_text()
        self.assertIn("  - outdated `barcode-capture-ios/references/api.md:1` (high)"
                      " ``Use `Scanner`  with a frame.`` — deprecated in 9.9.0", md)
        self.assertIn("  - not-covered `barcode-capture-ios` (medium) — new feedback API", md)

    def test_code_span_fences_past_inner_backticks(self):
        self.assertEqual(accuracy_review.code_span("a"), "`a`")
        self.assertEqual(accuracy_review.code_span("`x` ``y``"), "``` `x` ``y`` ```")
        self.assertEqual(accuracy_review.code_span(" a "), "`  a  `")


if __name__ == "__main__":
    unittest.main()
