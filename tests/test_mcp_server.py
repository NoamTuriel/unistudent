"""The MCP server: any MCP client (Claude, Cursor, VS Code, Codex, Gemini) gets the same commands as tools."""
import json
import os
import subprocess
import sys
import unittest

from helpers import SCRIPTS, CourseTestCase


class McpServer(CourseTestCase):
    def start(self):
        env = dict(os.environ, UNISTUDENT_HOME=str(self.home))
        return subprocess.Popen([sys.executable, str(SCRIPTS / "mcp_server.py")], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
                                encoding="utf-8")

    def rpc(self, proc, method, params=None, id_=1):
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    def setUp(self):
        super().setUp()
        self.proc = self.start()
        init = self.rpc(self.proc, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                                  "clientInfo": {"name": "test", "version": "0"}})
        self.assertEqual(init["result"]["serverInfo"]["name"], "unistudent")
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")

    def tearDown(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)
        self.proc.stdout.close()
        self.proc.stderr.close()
        super().tearDown()

    def call(self, name, arguments):
        reply = self.rpc(self.proc, "tools/call", {"name": name, "arguments": arguments}, id_=7)
        return reply["result"]

    def test_every_command_is_a_tool_named_after_it(self):
        names = {t["name"] for t in self.rpc(self.proc, "tools/list")["result"]["tools"]}
        for expected in ("setup", "courses_list", "courses_current", "wiki_build", "wiki_check", "add",
                         "check", "prefs_add", "study_changes", "study_mark_built", "ingest", "site_status",
                         "recordings_estimate", "recordings_fetch", "recordings_transcribe"):
            self.assertIn(expected, names)
        self.assertNotIn("eval_grade", names)  # a developer tool, not for students

    def test_tools_work_end_to_end(self):
        course = self.tmp / "Macro"
        own = self.tmp / "own"
        (own / "Unit 2").mkdir(parents=True)
        (own / "Unit 2" / "notes.txt").write_text("national accounting notes", "utf-8")
        result = self.call("setup", {"path": str(course), "name": "Macro", "language": "en",
                                     "import": str(own), "tier": "official"})
        self.assertFalse(result.get("isError"), result)
        data = json.loads(result["content"][0]["text"])
        self.assertEqual(data["imported"], 1)
        built = json.loads(self.call("wiki_build", {"course": str(course)})["content"][0]["text"])
        self.assertEqual(built["converted"], 1)
        current = json.loads(self.call("courses_current", {})["content"][0]["text"])
        self.assertEqual(current["name"], "Macro")

    def test_worker_instructions_and_rules_are_readable_through_the_server(self):
        docs = json.loads(self.call("doc", {})["content"][0]["text"])["docs"]
        self.assertTrue({"study-pack", "verifier", "source-reader", "study-pack-writer"} <= set(docs))
        text = json.loads(self.call("doc", {"name": "verifier"})["content"][0]["text"])["text"]
        self.assertIn("0 problems", text)

    def test_bad_input_never_kills_the_server(self):
        self.proc.stdin.write("not json\n")
        self.proc.stdin.flush()
        self.assertEqual(json.loads(self.proc.stdout.readline())["error"]["code"], -32700)
        self.proc.stdin.write("[1, 2]\n")
        self.proc.stdin.flush()
        self.assertEqual(json.loads(self.proc.stdout.readline())["error"]["code"], -32600)
        unknown = self.rpc(self.proc, "tools/call", {"name": "nope", "arguments": {}})
        self.assertEqual(unknown["error"]["code"], -32602)
        missing = self.call("assign", {})  # required arguments missing: argparse error text comes back
        self.assertTrue(missing["isError"])
        self.assertIn("required", missing["content"][0]["text"])
        self.assertIn("result", self.rpc(self.proc, "ping"))  # still alive

    def test_each_action_exposes_only_its_own_arguments(self):
        tools = {t["name"]: t["inputSchema"] for t in self.rpc(self.proc, "tools/list")["result"]["tools"]}
        self.assertEqual(tools["courses_list"]["properties"], {})
        self.assertEqual(tools["courses_switch"]["required"], ["target"])
        self.assertNotIn("force", tools["wiki_check"]["properties"])
        self.assertIn("text", tools["prefs_add"]["required"])

    def test_a_student_error_comes_back_as_a_tool_error(self):
        result = self.call("study_changes", {"course": str(self.tmp / "nowhere"), "unit": "4"})
        self.assertTrue(result["isError"])
        self.assertIn("No course folder found", result["content"][0]["text"])

    def test_skills_are_offered_as_prompts_for_clients_without_skills(self):
        prompts = {p["name"] for p in self.rpc(self.proc, "prompts/list")["result"]["prompts"]}
        self.assertTrue({"course-setup", "course-add", "course-wiki", "study-pack", "course-recordings", "course-help", "courses"} <= prompts)
        got = self.rpc(self.proc, "prompts/get", {"name": "course-add"})["result"]
        text = got["messages"][0]["content"]["text"]
        self.assertIn("inbox", text)
        self.assertNotIn("disable-model-invocation", text)  # frontmatter stripped


if __name__ == "__main__":
    unittest.main()
