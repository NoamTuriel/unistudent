"""Regressions found in code review, each at the seam where the student would notice."""
import os
import unittest

from helpers import CourseTestCase, make_pdf, mock_env, run, run_json, write


class Regressions(CourseTestCase):
    def test_recordings_with_the_same_name_in_different_sections_never_overwrite_each_other(self):
        local = self.tmp / "local"
        with mock_env(UNISTUDENT_RECORDINGS_ROOT=str(local), UNISTUDENT_STT_BACKEND="fake"):
            course = self.tmp / "Dropbox" / "Macro"
            run_json("setup", course, "--name", "Macro", "--language", "en")
            write(course / "inbox" / "Unit 1" / "session.mp4", b"\x01" * 2048)
            write(course / "inbox" / "Unit 2" / "session.mp4", b"\x02" * 2048)
            run_json("add", "--course", course)
            self.assertEqual((local / "Macro" / "inbox" / "Unit 1" / "session.mp4").read_bytes()[:1], b"\x01")
            self.assertEqual((local / "Macro" / "inbox" / "Unit 2" / "session.mp4").read_bytes()[:1], b"\x02")
            run_json("recordings", "transcribe", "--course", course, "inbox/Unit 1/session.mp4", "inbox/Unit 2/session.mp4")
        folders = sorted(p.parent.name for p in (course / "wiki" / "recordings").rglob("transcript.md"))
        self.assertEqual(folders, ["session", "session (2)"])

    def test_a_students_own_claude_md_is_kept(self):
        course = self.tmp / "Macro"
        write(course / "CLAUDE.md", "# My own notes\n\nAlways answer in Hebrew.\n")
        run_json("setup", course, "--name", "Macro")
        run_json("setup", self.tmp / "Stats", "--name", "Stats")  # rewrites other courses' context
        text = (course / "CLAUDE.md").read_text("utf-8")
        self.assertTrue(text.startswith("# My own notes"))
        self.assertIn("@.unistudent/context.md", text)
        self.assertEqual(text.count("@.unistudent/context.md"), 1)
        self.assertIn("Grounding labels", (course / ".unistudent" / "context.md").read_text("utf-8"))

    def test_the_course_context_reaches_every_agent(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro")
        self.assertIn("Grounding labels", (course / "AGENTS.md").read_text("utf-8"))
        self.assertIn("@.unistudent/context.md", (course / "CLAUDE.md").read_text("utf-8"))

    def test_a_students_own_agents_md_is_kept(self):
        course = self.tmp / "Macro"
        write(course / "AGENTS.md", "# Mine\n")
        run_json("setup", course, "--name", "Macro")
        run_json("setup", course, "--name", "Macro")
        text = (course / "AGENTS.md").read_text("utf-8")
        self.assertTrue(text.startswith("# Mine"))
        self.assertEqual(text.count(".unistudent/context.md"), 1)

    def test_where_an_added_file_comes_from_reaches_the_wiki(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        make_pdf(course / "inbox" / "Unit 3 summary.pdf", ["Unit 3 summary text"])
        run_json("add", "--course", course, "--describe", "Unit 3 summary.pdf=friend's summary")
        page = (course / "wiki" / "sources" / "unit-03" / "Unit 3 summary.md").read_text("utf-8")
        self.assertIn("origin_note: friend's summary", page)

    def test_a_bad_unit_is_a_message_not_a_crash(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro")
        code, out = run("study", "changes", "--course", course, "--unit", "four")
        self.assertEqual(code, 1)
        self.assertIn("A unit is a number", out)

    def test_an_edit_in_the_middle_of_a_file_is_noticed(self):
        own = self.tmp / "own"
        big = bytearray(b"a" * (3 << 20))
        write(own / "Unit 1" / "notes.txt", bytes(big))
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--import", own, "--tier", "official")
        big[len(big) // 2] = ord("b")
        write(own / "Unit 1" / "notes.txt", bytes(big))
        result = run_json("import", "--course", course, own, "--tier", "official")
        self.assertEqual(result["imported"], ["Unit 1/notes.txt"])

    def test_an_interrupted_sync_resumes_with_what_is_left(self):
        import json
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        staged = self.tmp / "staged"
        items = [{"url": "u1", "file": "a.pdf", "name": "a.pdf", "section": "Unit 1"},
                 {"url": "u2", "file": "b.pdf", "name": "b.pdf", "section": "Unit 2"}]
        listing = write(self.tmp / "listing.json", json.dumps({"items": items}))
        make_pdf(staged / "a.pdf", ["Unit 1"])  # the download stopped after a.pdf
        first = run_json("ingest", "--course", course, listing, staged)
        self.assertEqual((first["new"], first["missing"]), (["site/Unit 1/a.pdf"], ["u2"]))
        self.assertEqual(run_json("site-status", "--course", course)["downloaded"], ["u1"])
        make_pdf(staged / "b.pdf", ["Unit 2"])  # the fetcher resumes with what's missing
        second = run_json("ingest", "--course", course, listing, staged)
        self.assertEqual((second["new"], second["changed"], second["missing"]), (["site/Unit 2/b.pdf"], [], []))


if __name__ == "__main__":
    unittest.main()
