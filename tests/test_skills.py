"""Skills are portable Agent Skills: valid frontmatter, and the shared conventions block kept identical."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins" / "unistudent" / "scripts" / "unistudent" / "skills"
ALL = sorted(ROOT.glob("plugins/*/skills/*/SKILL.md")) + sorted(CORE.glob("*/SKILL.md"))
BLOCK = re.compile(r"<!-- conventions:.*?<!-- /conventions -->", re.S)


class Skills(unittest.TestCase):
    def test_every_skill_has_the_open_standard_frontmatter(self):
        self.assertGreaterEqual(len(ALL), 9)
        for skill in ALL:
            text = skill.read_text("utf-8")
            front = text.split("---")[1]
            name = re.search(r"(?m)^name:\s*\"?([^\"\n]+)", front).group(1).strip()
            description = re.search(r"(?m)^description:\s*(.+)$", front).group(1).strip().strip('"')
            self.assertRegex(name, r"^[a-z0-9-]{1,64}$", skill)
            self.assertEqual(name, skill.parent.name, skill)
            self.assertLessEqual(len(description), 1024, skill)

    def test_core_skills_share_one_conventions_block(self):
        blocks = {BLOCK.search(s.read_text("utf-8")).group(0) for s in CORE.glob("*/SKILL.md")}
        self.assertEqual(len(blocks), 1)

    def test_skills_name_no_client_specific_tools(self):
        for skill in ALL:
            text = BLOCK.sub("", skill.read_text("utf-8"))
            for word in ("AskUserQuestion", "Skill tool", "Glob for"):
                self.assertNotIn(word, text, skill)


if __name__ == "__main__":
    unittest.main()


class TranscriptionAndGraphRules(unittest.TestCase):
    """Ticket 17: the student picks recordings by number before any run, and graphs go through the tool first."""
    SKILLS = CORE

    def test_course_recordings_shows_a_numbered_list_before_the_first_transcription(self):
        text = (self.SKILLS / "course-recordings" / "SKILL.md").read_text("utf-8")
        self.assertIn("numbered list", text)
        self.assertIn("full path", text)
        self.assertIn('"All" is not an answer', text)
        self.assertLess(text.index("numbered list"), text.index("recordings approve"))
        self.assertLess(text.index("recordings approve"), text.index("recordings transcribe"))
        self.assertIn("Sit back and relax", text)

    def test_setup_transcribes_what_its_fetch_plan_approved_and_never_asks_per_recording(self):  # ADR 0013
        text = (self.SKILLS / "course-setup" / "SKILL.md").read_text("utf-8")
        self.assertNotIn("ask me per recording", text)
        self.assertLess(text.index("fetch-plan"), text.index("recordings transcribe"))

    RULES = (CORE.parent / "reference" / "study-pack.md").read_text("utf-8")

    def test_graph_instructions_name_the_mcp_tool_and_never_an_install(self):
        self.assertIn("MCP tool `graph` first", self.RULES)
        self.assertIn("The student is never told to install anything", self.RULES)
        self.assertLess(self.RULES.index("MCP tool `graph` first"), self.RULES.index("never told to install"))
        self.assertNotIn("pip install", self.RULES)
        self.assertIn("not a graph or a flow is a slide link plus one line in words", self.RULES)

    def test_the_roadmap_rule_holds_the_one_discovery_sentence(self):
        sentence = "UniStudent draws graphs and flowcharts on request"
        roadmap = self.RULES.split("## Roadmap page")[1].split("\n## ")[0]
        self.assertIn(sentence, roadmap)
        self.assertEqual(self.RULES.count(sentence), 1)
        for skill in ALL:
            self.assertNotIn(sentence, skill.read_text("utf-8"), skill)

    def test_no_skill_names_the_removed_picture_commands(self):
        for doc in ALL + [CORE.parent / "reference" / "study-pack.md"] + sorted((CORE.parent / "agents").glob("*.md")):
            text = doc.read_text("utf-8")
            for gone in ("us draw", "tools status", "tools offer", "tools accept", "tools skip"):
                self.assertNotIn(gone, text, doc)


class FormFollowsTheCourse(unittest.TestCase):
    """Ticket 26: a concept takes the form its source uses, recorded per topic as the unit's Presentation."""
    AGENTS = CORE.parent / "agents"

    def test_the_unit_writer_writes_the_presentation_section_with_the_kind_words(self):
        text = (self.AGENTS / "wiki-unit-writer.md").read_text("utf-8")
        self.assertIn("`## Presentation`", text)
        for kind in ("table", "steps", "flowchart", "graph", "picture", "circuit", "molecule", "3D model"):
            self.assertIn(f"`{kind}`", text)

    def test_the_rules_hold_the_form_sentence_and_the_checklist(self):
        concepts = TranscriptionAndGraphRules.RULES.split("## Concepts (walkthrough)")[1].split("\n## ")[0]
        self.assertIn("A concept is presented in the form its source uses", concepts)
        self.assertIn("coverage checklist", concepts)
        for part in ("what it is", "why it is so", "formula", "memory tip"):
            self.assertIn(part, concepts.lower())

    def test_the_pack_writer_opens_the_page_the_presentation_line_names(self):
        text = (self.AGENTS / "study-pack-writer.md").read_text("utf-8")
        self.assertIn("Presentation", text)
        self.assertIn("copy its form", text)


class UnattendedBuild(unittest.TestCase):
    """Ticket 28: a build the student starts and walks away from: it never asks, and it resumes."""
    SKILL = (CORE / "study-pack" / "SKILL.md").read_text("utf-8")

    def test_no_step_asks_the_student_during_a_build(self):
        build = self.SKILL[self.SKILL.index("## 3."):self.SKILL.index("## 7.")]
        writer = (CORE.parent / "agents" / "study-pack-writer.md").read_text("utf-8")
        for text in (build, writer):
            self.assertIsNone(re.search(r"(?i)\bask|interview|\bconfirm", text))

    def test_the_skill_names_the_resume_rules(self):
        for rule in ("pages_present", "only when the request named it", "one line", "lessons_without_roadmap",
                     "us wiki build"):
            self.assertIn(rule, self.SKILL)
        self.assertLess(self.SKILL.index("lessons_without_roadmap"), self.SKILL.index("study-pack-writer"))


class NoSubjectLayer(unittest.TestCase):
    """Ticket 25 (ADR 0011): rules come from three layers, and nothing names a course skill or a field skill."""

    def test_no_skill_template_agent_or_rule_names_a_course_or_field_skill(self):
        texts = ALL + sorted((CORE.parent).glob("*/*.md"))
        for path in texts:
            self.assertIsNone(re.search(r"(?i)course[ _-]skill|field[ _-]skill", path.read_text("utf-8")), path)

    def test_the_study_pack_skill_names_exactly_three_rule_layers(self):
        skill = (CORE / "study-pack" / "SKILL.md").read_text("utf-8")
        rules = skill[skill.index("## 3."):skill.index("## 4.")]
        self.assertEqual(re.findall(r"(?m)^\d+\. ", rules), ["1. ", "2. ", "3. "])
        for layer in ("generic rules", "General preferences", "Course preferences"):
            self.assertIn(layer, rules)


class WorkersGetTheTools(unittest.TestCase):
    """Ticket 27: every worker can call the UniStudent tools; the verifier checks graphs; Short version from solutions."""
    AGENTS = CORE.parent / "agents"

    def test_every_registered_worker_lists_the_unistudent_tools(self):
        manifest = (ROOT / "plugins" / "unistudent" / ".claude-plugin" / "plugin.json").read_text("utf-8")
        workers = sorted(self.AGENTS.glob("*.md"))
        self.assertEqual(len(workers), 7)
        for skill in sorted(CORE.glob("*/SKILL.md")):
            self.assertIn(f"./scripts/unistudent/skills/{skill.parent.name}\"", manifest)
        for worker in workers:
            self.assertIn(f"./scripts/unistudent/agents/{worker.name}", manifest)
            tools = re.search(r"(?m)^tools:(.*)$", worker.read_text("utf-8")).group(1)
            self.assertIn("mcp__plugin_unistudent_unistudent", tools, worker)

    def test_the_conventions_block_has_other_apps_run_the_worker_steps_in_the_main_agent(self):
        block = BLOCK.search((CORE / "study-pack" / "SKILL.md").read_text("utf-8")).group(0)
        self.assertIn("in any other app, follow them yourself", block)

    def test_the_verifier_opens_every_graph_beside_its_slide(self):
        text = (self.AGENTS / "verifier.md").read_text("utf-8")
        steps = text.split("Done when")[0]
        for words in ("every embedded Graph", "PNG", "slide page its caption cites", "curves", "labels",
                      "crossings", "relative positions", "independently of the writer"):
            self.assertIn(words, steps)

    def test_the_short_version_is_grouped_from_both_solutions_always(self):
        rules = (CORE.parent / "reference" / "study-pack.md").read_text("utf-8")
        short = rules.split("### Short version")[1].split("\n#")[0]
        self.assertNotIn("when unsure", short.lower())
        self.assertIn("read both solutions", short)


class RulesByPath(unittest.TestCase):
    """Ticket 29: the writer and verifier read the three rule files themselves; nothing is pasted."""
    SKILL = (CORE / "study-pack" / "SKILL.md").read_text("utf-8")

    def test_the_skill_passes_three_rule_paths_to_the_writer_and_the_verifier(self):
        self.assertNotIn("paste", self.SKILL.lower())
        for step in ("## 5.", "## 6."):
            text = self.SKILL[self.SKILL.index(step):].split("\n## ")[0]
            self.assertIn("three rule paths", text)
        for worker in ("study-pack-writer.md", "verifier.md"):
            text = (CORE.parent / "agents" / worker).read_text("utf-8")
            for layer in ("generic rules", "General preferences", "Course preferences"):
                self.assertIn(layer, text, worker)

    def test_links_are_one_per_recording_per_section_and_a_question_without_an_anchor_is_named(self):
        rules = (CORE.parent / "reference" / "study-pack.md").read_text("utf-8")
        self.assertIn("one `file:` link per recording per section", rules)
        self.assertIn("no page anchor", rules.split("## Practice page")[1].split("\n## ")[0])


class RecommendedTools(unittest.TestCase):
    """Ticket 32 (ADR 0012): recommended tools on paper: the rules section, the harness table, the roadmap line."""
    RULES = (CORE.parent / "reference" / "study-pack.md").read_text("utf-8")

    def section(self):
        return self.RULES.split("## Recommended tools")[1].split("\n## ")[0]

    def test_the_section_holds_every_rule_and_one_harness_row_per_app(self):
        section = self.section()
        for rule in ("**Tool bar.**", "**Boundary.**", "**Harness table.**", "**Entry rule.**",
                     "**Unattended surface.**", "uv run --with", "proven by one sample call in CI",
                     "needs a restart", "`us tools add <name>`", "no keyword pre-scan"):
            self.assertIn(rule, section)
        rows = [line for line in section.splitlines() if line.startswith("| ") and "---" not in line][1:]
        for app, where in (("Claude Code", "`.mcp.json`"), ("Cursor", "`.cursor/mcp.json`"),
                           ("Codex", "`.codex/config.toml`"), ("Gemini CLI", "`.gemini/settings.json`"),
                           ("VS Code", "`.vscode/mcp.json`"), ("Claude Desktop", "name it and give the steps"),
                           ("Cowork", "name it and give the steps"), ("Any other app", "name it and give the steps")):
            row = next(r for r in rows if r.startswith(f"| {app} "))
            self.assertIn(where, row)

    def test_the_roadmap_closing_line_names_the_per_kind_sentence(self):
        how_to_start = self.RULES.split("## Roadmap page")[1].split("\n2. ")[0]
        closing = how_to_start.split("on request")[1]
        for words in ("study-pack skill", "Recommended tools"):
            self.assertIn(words, closing)
        build = (CORE / "study-pack" / "SKILL.md").read_text("utf-8").split("## 5. Build")[1].split("\n## ")[0]
        for words in ("`picture` gap", "Presentation kind words", "Tool list", "per missing kind", "`rule`"):
            self.assertIn(words, build)

    def test_no_rule_asks_the_student_during_the_build(self):
        self.assertIsNone(re.search(r"(?i)\bask|interview|\bconfirm", self.section()))


class OpenUSync(unittest.TestCase):
    """Ticket 36: scan without downloading, the Fetch plan on every sync, stream links only after the OK."""
    SYNC = ROOT / "plugins" / "openu" / "skills" / "openu-sync"
    TEXT = (SYNC / "SKILL.md").read_text("utf-8")
    SITE = (SYNC / "references" / "site.md").read_text("utf-8")

    def step(self, title):
        return self.TEXT.split(f". {title}\n")[1].split("\n## ")[0]

    def test_no_recordings_question_when_settings_hold_the_choices(self):
        self.assertIn("`recording_level`", self.TEXT)
        self.assertIn("Ask the recordings question only when `recording_level` is `null`", self.TEXT)
        self.assertNotIn("full video or audio only", self.TEXT)
        self.assertNotIn("Recordings: ask first", self.TEXT)

    def test_stream_links_are_collected_only_after_the_ok(self):
        scan = self.step("Scan, without downloading")
        self.assertIn("no stream links", scan)
        self.assertNotIn("stream snippet", scan)
        self.assertLess(self.TEXT.index("fetch-plan apply"), self.TEXT.index("stream snippet"))
        self.assertIn("collect its link again once", self.TEXT)
        self.assertIn("only after the student's OK", self.SITE)

    def test_the_fetch_plan_shows_on_every_sync_before_any_download(self):
        plan = self.step("The Fetch plan")
        self.assertIn("every sync", plan)
        for choice in ("download all", "skip all recordings", "edit the list"):
            self.assertIn(choice, plan)
        self.assertIn("explicit OK", plan)
        self.assertLess(self.TEXT.index("fetch-plan show"), self.TEXT.index("download every document item"))
        self.assertIn("`nothing_new`", plan)  # the Fetch plan itself leaves out what is already downloaded
        self.assertIn('"Nothing new on the site since <date>"', plan)

    def test_sorting_is_asked_before_the_download_inside_setup_and_after_it_outside(self):
        self.assertIn("I don't know", self.step("The Fetch plan"))
        self.assertIn("I don't know", self.step("Report"))
        self.assertIn("Inside setup", self.step("Report"))

    def test_recordings_are_skipped_only_by_choice_and_the_sound_only_rule_lives_in_the_command(self):
        scan = self.step("Scan, without downloading")
        self.assertIn("skip them when `recording_level` is 0", scan)
        self.assertNotIn("keep_video", scan)
        self.assertNotIn("--audio-only", self.TEXT)  # `us recordings fetch` applies the Settings itself

    def test_a_batch_of_recordings_builds_the_wiki_once(self):
        recordings = self.step("Download the recordings, one at a time")
        self.assertIn("--no-wiki", recordings)
        self.assertLess(recordings.index("--no-wiki"), recordings.index("us wiki build"))

    def test_site_notes_mark_the_live_unknowns_and_the_corrected_size(self):
        self.assertIn("about 2.4 GB", self.SITE)
        self.assertNotIn("3 GB", self.SITE)
        self.assertIn("method: 'HEAD'", self.SITE)
        self.assertGreaterEqual(self.SITE.count("Unverified"), 2)
