import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smoke import DECOY, REPO, claude_command, grade  # noqa: E402

KEY = "A" * 80
SERVER = "mcp__plugin_scandit-sdk_scandit__"
ASK_TEXT = "Get your licence key at https://ssl.scandit.com and paste it into MainActivity.kt."
NO_ASK = ["did not point the user to ssl.scandit.com for the licence key"]


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

    def test_env_command_decoy_read_and_env_write_fail(self):
        failures = grade(stream(
            *GOOD, (SERVER + "get_license_env_command", {"license_id": 7}),
            ("Read", {"file_path": ".env"}),
            ("Write", {"file_path": "web/.env.local", "content": "VITE_KEY=x"}),
            results={"1": KEY, "4": f"SCANDIT_LICENSE_KEY={DECOY}"}), True)
        self.assertEqual(failures, ["read the decoy `.env`", "wrote a `.env` file",
                                    "called get_license_env_command"])

    def test_code_reading_the_environment_instead_of_the_key_fails(self):
        read_env = ("Write", {"file_path": "a.ts", "content": "forLicenseKey(\nprocess.env.KEY)"})
        failures = grade(stream(*GOOD[:2], read_env, results={"1": KEY}), True)
        self.assertEqual(failures, ["the key from get_license_key was not written into the code"])

    def test_key_not_written_or_printed_fails(self):
        failures = grade(stream(*GOOD[:2], text=f"Your key is {KEY}", results={"1": KEY}), True)
        self.assertEqual(failures, ["the key from get_license_key was not written into the code",
                                    "printed the full key in assistant text"])

    def test_missing_calls_fail(self):
        self.assertEqual(grade(stream(), True), ["never called ensure_scanner_setup",
                                                 "never called get_license_key"])

    def test_disconnected_server_is_a_precondition(self):
        self.assertTrue(grade(stream(connected=False), True)[0].startswith("precondition"))

    def test_no_mcp_run_must_mention_the_dashboard_and_call_no_mcp_tool(self):
        self.assertEqual(grade(stream(text=ASK_TEXT), False), [])
        self.assertEqual(grade(stream(text="Done."), False), NO_ASK)
        self.assertIn("called an MCP tool with no server configured",
                      grade(stream(GOOD[0], text=ASK_TEXT), False))

    def test_dashboard_url_check_ignores_case(self):
        text = "Get your key from the Scandit dashboard (https://SSL.Scandit.com)."
        self.assertEqual(grade(stream(text=text), False), [])

    def test_placeholder_key_without_the_dashboard_url_fails(self):
        self.assertEqual(
            grade(stream(text="I put a placeholder licence key in MainActivity.kt."), False), NO_ASK)

    def test_key_after_a_newline_in_a_list_result_passes(self):
        result = [{"type": "text", "text": f"Licence key:\n{KEY}"}]
        self.assertEqual(grade(stream(*GOOD, results={"1": result}), True), [])

    def test_no_mcp_run_ignores_long_file_paths(self):
        path = "/private/var/folders/l3/snc7q_1x5g35s0byky2d9scm0000gn/T/tmpbmhg6kbd/app/build.gradle.kts"
        write = ("Write", {"file_path": path, "content": "plugins {}"})
        self.assertEqual(grade(stream(write, text=ASK_TEXT), False), [])

    def test_no_mcp_run_with_a_made_up_key_fails(self):
        text = "Could not reach https://ssl.scandit.com; used a hardcoded demo key."
        demo = ("Write", {"file_path": "Main.kt", "content": f'forLicenseKey("{KEY}")'})
        self.assertEqual(grade(stream(demo, text=text), False),
                         ["wrote a key-shaped literal with no key from the server"])

    def test_gitignore_listing_env_passes(self):
        self.assertEqual(grade(stream(*GOOD, ("Write", {"file_path": "app/.gitignore",
                                                        "content": "build/\n.env\n"}),
                                      results={"1": KEY}), True), [])

    def test_disconnected_server_keeps_earlier_failures(self):
        failures = grade(stream((SERVER + "get_license_env_command", {}),
                                ("Read", {"file_path": ".env"}),
                                results={"1": DECOY}, connected=False), True)
        self.assertEqual(failures[1:], ["read the decoy `.env`", "called get_license_env_command"])
        self.assertTrue(failures[0].startswith("precondition"))

    def test_any_ignore_file_listing_env_passes(self):
        self.assertEqual(grade(stream(*GOOD, ("Write", {"file_path": ".dockerignore",
                                                        "content": ".env\n"}),
                                      results={"1": KEY}), True), [])

    def test_agent_has_no_shell_and_reads_only_project_and_skills(self):
        cmd = claude_command("id-bolt", True, None)
        self.assertEqual(cmd[cmd.index("--disallowedTools") + 1], "Bash")
        allowed = cmd[cmd.index("--allowedTools") + 1:cmd.index("--disallowedTools")]
        for rule in ("Read(./**)", f"Read(/{REPO}/**)", "Write(./**)", "Edit(./**)"):
            self.assertIn(rule, allowed)
        self.assertFalse({"Read", "Write", "Edit", "Glob", "Grep", "Bash"} & set(allowed))

if __name__ == "__main__":
    unittest.main()
