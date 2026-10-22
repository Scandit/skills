import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke import grade  # noqa: E402

KEY = "A" * 80
SERVER = "mcp__plugin_scandit-sdk_scandit__"


def stream(*calls, text="Done.", results=None, connected=True):
    init = {"type": "system", "subtype": "init",
            "mcp_servers": [{"name": "plugin:scandit-sdk:scandit",
                             "status": "connected" if connected else "failed"}]}
    uses = [{"type": "tool_use", "id": str(i), "name": n, "input": inp}
            for i, (n, inp) in enumerate(calls)]
    tool_results = [{"type": "tool_result", "tool_use_id": i, "content": c}
                    for i, c in (results or {}).items()]
    return [json.dumps(e) for e in (
        init,
        {"type": "assistant", "message": {"content": uses}},
        {"type": "user", "message": {"content": tool_results}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}},
    )]


GOOD = (
    (SERVER + "ensure_scanner_setup", {"env_var": "SCANDIT_LICENSE_KEY", "env_file": ".env"}),
    (SERVER + "get_license_key", {"license_id": 7}),
    ("Write", {"file_path": "Main.kt", "content": f'DataCaptureContext.forLicenseKey("{KEY}")'}),
)


class GradeTest(unittest.TestCase):
    def test_key_from_server_into_code_passes(self):
        self.assertEqual(grade(stream(*GOOD, results={"1": json.dumps({"key": KEY})}), True), [])

    def test_env_command_and_env_reads_fail(self):
        failures = grade(stream(
            *GOOD, (SERVER + "get_license_env_command", {"license_id": 7}),
            ("Bash", {"command": "cat .env"}),
            ("Write", {"file_path": "a.ts", "content": "import.meta.env.VITE_SCANDIT_LICENSE_KEY"}),
            results={"1": KEY}), True)
        self.assertIn("called get_license_env_command", failures)
        self.assertEqual(sum("touches `.env`" in f for f in failures), 2)

    def test_key_not_written_or_printed_fails(self):
        failures = grade(stream(*GOOD[:2], text=f"Your key is {KEY}", results={"1": KEY}), True)
        self.assertEqual(failures, ["the key from get_license_key was not written into the code",
                                    "printed the full key in assistant text"])

    def test_missing_calls_fail(self):
        self.assertEqual(grade(stream(), True), ["never called ensure_scanner_setup",
                                                 "never called get_license_key"])

    def test_disconnected_server_is_a_precondition(self):
        self.assertTrue(grade(stream(connected=False), True)[0].startswith("precondition"))

    def test_no_mcp_run_must_ask_for_the_key(self):
        self.assertEqual(grade(stream(text="Paste your Scandit licence key."), False), [])
        self.assertEqual(grade(stream(text="Done."), False),
                         ["did not ask the user for the licence key"])
        self.assertIn("called an MCP tool with no server configured",
                      grade(stream(GOOD[0], text="Paste your licence key."), False))


if __name__ == "__main__":
    unittest.main()
