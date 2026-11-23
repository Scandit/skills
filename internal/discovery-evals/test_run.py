import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import codex
import run


class MatrixTest(unittest.TestCase):
    def test_failed_observations_do_not_cancel_remaining_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "matrix"
            attempted = []
            first = out / "codex" / codex.MODELS[0] / "toolbar-controlled" / "baseline"

            def execute(args, **kwargs):
                script = Path(args[1]).name
                if script == "codex.py":
                    dest = args[args.index("--out") + 1]
                    attempted.append(dest)
                    return subprocess.CompletedProcess(args, int(dest == first))
                return subprocess.CompletedProcess(args, int(script == "claude.py"))

            with patch.object(run, "stage"), patch.object(run, "stage_guides"), \
                    patch.object(run.subprocess, "run", side_effect=execute):
                with self.assertRaises(SystemExit) as error:
                    run.matrix(out, "controlled-toolbar")

            self.assertEqual(attempted, [
                out / "codex" / model / "toolbar-controlled" / variant
                for model in codex.MODELS for variant in ("baseline", "split")
            ])
            self.assertEqual(str(error.exception).splitlines()[1:],
                             [str(out / "claude" / "initial"), str(first)])


class CodexResultTest(unittest.TestCase):
    def test_warnings_and_blank_lines_are_retained_with_successful_usage(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)
            project = dest / "project"
            usage = {"input_tokens": 10, "output_tokens": 2}
            event = json.dumps({"type": "turn.completed", "usage": usage})
            stdout = f"warning from {project}\n\n{event}\ntrailing note\n"
            codex.record_result(subprocess.CompletedProcess([], 0, stdout, "diagnostic"), dest, project)
            self.assertEqual(json.loads((dest / "usage.json").read_text()), usage)
            self.assertEqual((dest / "events.jsonl").read_text(), stdout.replace(str(project), "<project>"))
            self.assertEqual((dest / "stderr.log").read_text(), "diagnostic")

    def test_incomplete_runs_keep_diagnostics_without_recording_usage(self):
        completed = '{"type":"turn.completed","usage":{"input_tokens":10}}\n'
        errors = [(1, completed), (0, "warning only\n"), (0, '{"type":"turn.completed"}'),
                  (0, completed + '{"type":"error"}\ntrailing note\n')]
        for code, stdout in errors:
            with self.subTest(code=code, stdout=stdout), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp)
                with self.assertRaisesRegex(RuntimeError, "Run incomplete.*events.jsonl and stderr.log"):
                    codex.record_result(subprocess.CompletedProcess([], code, stdout, "diagnostic"),
                                        dest, dest / "project")
                self.assertEqual((dest / "events.jsonl").read_text(), stdout)
                self.assertEqual((dest / "stderr.log").read_text(), "diagnostic")
                self.assertFalse((dest / "usage.json").exists())
