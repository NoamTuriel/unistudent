"""Seam 2: a small course folder → the expected Wiki pages."""
import shutil
import unittest

from helpers import CourseTestCase, can_read_pdfs, folders, make_pdf, run, run_json, write


def make_docx(path, paragraphs):
    import docx
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(path))


class WikiBuild(CourseTestCase):
    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        make_pdf(own / "Unit 4 - money" / "slides.pdf", ["Money multiplier is 1 over r", "Reserve ratio example"])
        make_pdf(own / "exams" / "exam 2024.pdf", ["Question 1 on the multiplier"])
        write(own / "Unit 5" / "notes.txt", "Open market operations change the monetary base.")
        write(own / "recordings" / "session 1.mp4", b"\x00" * 1024)
        self.own = own
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        self.wiki = folders(self.course).wiki

    def build(self, *extra):
        return run_json("wiki", "build", "--course", self.course, *extra)

    def test_every_document_becomes_a_markdown_source_page_with_its_pages_and_origin(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        self.build()
        page = (self.wiki / "sources" / "unit-04" / "slides.md").read_text("utf-8")
        self.assertIn("source: official/Unit 4/slides.pdf", page)
        self.assertIn("tier: official", page)
        self.assertIn("## Page 1", page)
        self.assertIn("Money multiplier is 1 over r", page)
        self.assertIn("## Page 2", page)
        self.assertIn("Reserve ratio example", page)
        self.assertIn("Open market operations", (self.wiki / "sources" / "unit-05" / "notes.md").read_text("utf-8"))

    def test_word_files_are_converted(self):
        try:
            make_docx(self.own / "Unit 5" / "answers.docx", ["The multiplier falls when r rises."])
        except ImportError:
            self.skipTest("python-docx not installed")
        run("import", "--course", self.course, self.own, "--tier", "official")
        self.build()
        self.assertIn("The multiplier falls when r rises.",
                      (self.wiki / "sources" / "unit-05" / "answers.md").read_text("utf-8"))

    def test_index_unit_pages_and_stubs_exist_and_recordings_are_listed_not_converted(self):
        result = self.build()
        index = (self.wiki / "index.md").read_text("utf-8")
        self.assertIn("units/unit-04.md", index)
        self.assertIn("units/unit-05.md", index)
        self.assertIn("glossary.md", index)
        self.assertIn("question-bank.md", index)
        unit4 = (self.wiki / "units" / "unit-04.md").read_text("utf-8")
        self.assertIn("../sources/unit-04/slides.md", unit4)
        for stub in ("glossary.md", "question-bank.md", "course.md"):
            self.assertTrue((self.wiki / stub).exists(), stub)
        self.assertIn("official/Unsorted/session 1.mp4", result["recordings"])
        self.assertFalse(list(self.wiki.rglob("session 1*.md")))

    def test_a_fresh_wiki_passes_the_check(self):
        self.build()
        report = run_json("wiki", "check", "--course", self.course)
        self.assertEqual(report["problems"], [])

    def test_check_finds_broken_links_and_pages_without_sources(self):
        self.build()
        write(self.wiki / "topics" / "bad.md", "# Bad\n\nSee [missing](../sources/nope.md).\n")
        problems = run_json("wiki", "check", "--course", self.course)["problems"]
        kinds = sorted(p["kind"] for p in problems)
        self.assertEqual(kinds, ["broken-link", "no-sources"])

    def test_a_page_of_entries_citing_the_material_needs_no_page_level_sources_line(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        self.build()
        (self.wiki / "glossary.md").write_text(
            "# Glossary\n\n### Money multiplier\nIt is 1/r. [slides](sources/unit-04/slides.md#page-1)\n", "utf-8")
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_unchanged_files_are_not_converted_again(self):
        first = self.build()
        self.assertEqual(first["converted"], 3)
        second = self.build()
        self.assertEqual(second["converted"], 0)

    def test_deleting_the_wiki_and_rebuilding_gives_the_same_pages(self):
        self.build()
        before = {p.relative_to(self.wiki).as_posix(): p.read_text("utf-8") for p in self.wiki.rglob("*.md")}
        shutil.rmtree(self.wiki)
        self.build()
        after = {p.relative_to(self.wiki).as_posix(): p.read_text("utf-8") for p in self.wiki.rglob("*.md")}
        self.assertEqual(before, after)

    def test_what_claude_wrote_in_a_unit_page_survives_a_rebuild(self):
        self.build()
        unit4 = self.wiki / "units" / "unit-04.md"
        unit4.write_text(unit4.read_text("utf-8") + "\n## Approved methods\n\n- The five steps. Sources: [slides](../sources/unit-04/slides.md#page-1)\n", "utf-8")
        make_pdf(self.own / "Unit 4 - money" / "more.pdf", ["Extra example"])
        run("import", "--course", self.course, self.own, "--tier", "official")
        self.build()
        text = unit4.read_text("utf-8")
        self.assertIn("The five steps", text)
        self.assertIn("../sources/unit-04/more.md", text)

    def test_the_presentation_section_survives_a_rebuild(self):
        self.build()
        unit4 = self.wiki / "units" / "unit-04.md"
        unit4.write_text(unit4.read_text("utf-8") + "\n## Presentation\n\n- table, page 2: reserve ratio example\n", "utf-8")
        make_pdf(self.own / "Unit 4 - money" / "more.pdf", ["Extra example"])
        run("import", "--course", self.course, self.own, "--tier", "official")
        self.build()
        self.assertIn("## Presentation\n\n- table, page 2: reserve ratio example", unit4.read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
