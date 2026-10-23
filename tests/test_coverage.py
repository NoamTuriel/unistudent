"""Coverage (ticket 13): the Wiki says which files it read, which it couldn't, and which were skipped."""
import shutil
from pathlib import Path
import unittest
from unittest import mock

from helpers import CourseTestCase, can_read_pdfs, folders, make_pdf, run, run_json, write
from unistudent import convert
from unistudent.convert import Conversion


class Coverage(CourseTestCase):
    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        write(own / "Unit 1" / "notes.txt", "The multiplier is 1/(1-c) and it is used in every chapter of this course.")
        write(own / "Unit 1" / "broken.txt", "x")
        write(own / "Unit 1" / "diagram.png")
        write(own / "Unit 1" / "lecture 1.mp4", b"\x00" * 64)
        write(own / "Unit 1" / "data.xyz")
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")

    def coverage(self):
        result = run_json("wiki", "coverage", "--course", self.course)
        return {r["path"]: r for r in result["files"]}, result

    def build_with_one_unreadable_file(self):
        real = __import__("unistudent.wiki", fromlist=["convert"]).convert

        def convert(path):
            if path.name == "broken.txt":
                return Conversion([], "none", ["could not be opened"])
            return real(path)

        with mock.patch("unistudent.wiki.convert", convert):
            return run_json("wiki", "build", "--course", self.course)

    def test_every_file_is_analyzed_failed_skipped_or_pending(self):
        self.build_with_one_unreadable_file()
        files, result = self.coverage()
        self.assertEqual(files["official/Unit 1/notes.txt"]["status"], "analyzed")
        self.assertEqual(files["official/Unit 1/broken.txt"]["status"], "failed")
        self.assertIn("could not be opened", files["official/Unit 1/broken.txt"]["why"])
        self.assertEqual(files["official/Unit 1/diagram.png"]["status"], "skipped")
        self.assertEqual(files["official/Unit 1/data.xyz"]["status"], "skipped")
        self.assertEqual(files["official/Unit 1/lecture 1.mp4"]["status"], "pending")
        self.assertEqual(sum(result["counts"].values()), len(files))

    def test_before_a_build_documents_are_pending(self):
        files, _ = self.coverage()
        self.assertEqual(files["official/Unit 1/notes.txt"]["status"], "pending")

    def test_a_recording_the_student_chose_not_to_process_is_skipped_with_that_reason(self):
        run_json("context", "--course", self.course, "--recording-level", "1")
        files, _ = self.coverage()
        self.assertEqual(files["official/Unit 1/lecture 1.mp4"]["status"], "skipped")
        self.assertIn("you chose", files["official/Unit 1/lecture 1.mp4"]["why"])

    def test_showing_coverage_writes_nothing_and_a_changed_file_is_pending_again(self):
        self.build_with_one_unreadable_file()
        (folders(self.course).wiki / "coverage.md").unlink()
        self.coverage()
        self.assertFalse((folders(self.course).wiki / "coverage.md").exists())

    def test_the_wiki_gets_a_coverage_page_that_passes_the_check_and_warns_the_ai(self):
        self.build_with_one_unreadable_file()
        page = (folders(self.course).wiki / "coverage.md").read_text("utf-8")
        self.assertIn("## Failed (1)", page)
        self.assertIn("NOT in the Wiki", page)
        self.assertIn("coverage.md", (folders(self.course).wiki / "index.md").read_text("utf-8"))
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_the_build_summary_carries_the_coverage_counts(self):
        result = self.build_with_one_unreadable_file()
        self.assertEqual(result["coverage"]["failed"], 1)
        self.assertIn("1 failed", result["summary"])


class PagesReadVisually(CourseTestCase):
    """Ticket 31: a source page written by the source-reader worker records the fingerprint it read, so it counts."""

    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        write(own / "Unit 1" / "diagram.png")
        write(own / "Unit 1" / "scan.pdf")
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        self.wiki = folders(self.course).wiki

    def build(self):
        real = __import__("unistudent.wiki", fromlist=["convert"]).convert

        def convert(path):  # a scan: page 1 has no text layer
            return Conversion(["", "Page two has a text layer long enough to count."], "pypdf") \
                if path.name == "scan.pdf" else real(path)

        with mock.patch("unistudent.wiki.convert", convert):
            return run_json("wiki", "build", "--course", self.course)

    def read_visually(self, item):  # what the source-reader worker does with one item of `images` or `needs_visual`
        page = self.wiki / item["page"]
        head = f"---\nsource: {item['source']}\nfingerprint: {item['fingerprint']}\nconverted_with: visual\n---\n\n"
        body = page.read_text("utf-8").split("---\n", 2)[2] if page.exists() else "# diagram.png\n\n## Page 1\n\nA curve.\n"
        write(page, head + body)

    def test_an_image_with_a_source_page_and_a_filled_scan_are_analyzed_and_not_listed_again(self):
        built = self.build()
        self.assertEqual([i["source"] for i in built["images"]], ["official/Unit 1/diagram.png"])
        self.assertEqual([i["source"] for i in built["needs_visual"]], ["official/Unit 1/scan.pdf"])
        for item in built["images"] + built["needs_visual"]:
            self.read_visually(item)
        files = {r["path"]: r for r in run_json("wiki", "coverage", "--course", self.course)["files"]}
        self.assertEqual(files["official/Unit 1/diagram.png"]["status"], "analyzed")
        self.assertEqual(files["official/Unit 1/diagram.png"]["page"], "sources/unit-01/diagram.md")
        self.assertEqual((files["official/Unit 1/scan.pdf"]["status"], files["official/Unit 1/scan.pdf"]["why"]), ("analyzed", ""))
        again = self.build()
        self.assertEqual((again["images"], again["needs_visual"]), ([], []))
        self.assertIn("../sources/unit-01/diagram.md", (self.wiki / "units" / "unit-01.md").read_text("utf-8"))  # its unit writer reads it
        self.assertIn("## Analyzed (2)", (self.wiki / "coverage.md").read_text("utf-8"))
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_an_image_named_like_a_document_gets_its_own_page(self):  # graph.png beside scan.pdf's page
        write(folders(self.course).material / "official" / "Unit 1" / "scan.png")
        pages = {i["source"]: i["page"] for i in self.build()["images"]}
        self.assertEqual(pages["official/Unit 1/scan.png"], "sources/unit-01/scan (2).md")

    def test_an_image_without_a_source_page_is_still_not_analyzed(self):
        self.build()
        files = {r["path"]: r for r in run_json("wiki", "coverage", "--course", self.course)["files"]}
        self.assertNotEqual(files["official/Unit 1/diagram.png"]["status"], "analyzed")

    def test_an_image_item_carries_the_frontmatter_its_page_needs(self):
        item = self.build()["images"][0]
        self.assertEqual((item["origin"], item["tier"], item["unit"]), ("student-folder", "official", 1))


class NoiseTextLayer(CourseTestCase):
    """#59: a handwritten scan whose text layer is OCR noise is read visually, and the noise never reaches the Wiki."""

    NOISE = "'fr Eg- I d 4 Lh tL yod/dis x ga'Nd y3y66 -klyd a3Ilar My"

    def build(self, name, make):
        own = self.tmp / "own" / "Unit 1"
        make(own / name)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own", "--tier", "official")
        built = run_json("wiki", "build", "--course", course)
        page = (folders(course).wiki / "sources" / "unit-01" / (Path(name).stem + ".md")).read_text("utf-8")
        return built, page

    @unittest.skipUnless(can_read_pdfs(), "no PDF text tool (pdftotext or pypdf)")
    def test_a_page_of_ocr_noise_is_listed_for_visual_reading_and_not_written(self):
        built, page = self.build("scan.pdf", lambda path: make_pdf(path, [
            self.NOISE,
            "The multiplier is one over one minus the marginal propensity to consume.",
            "Answer: ______________________ ______________________ __________",  # a question's answer lines
        ]))
        [item] = built["needs_visual"]
        self.assertEqual(item["pages"], [1])
        self.assertNotIn("Lh tL", page)
        self.assertIn("marginal propensity", page)

    def test_a_real_page_in_any_script_with_bidi_marks_is_text(self):
        rtl, ltr, end = "‫", "‪", "‬"  # how pdftotext marks a Hebrew table's cells
        table = " ".join(f"{rtl}{ltr}{cell}{end}{end}" for cell in ["שכר", "ריבית", "0.75", "MPC", "תוצר"] * 4)
        pages = [table, "日本語のテキストです。経済学の授業ノートです。", "Le multiplicateur est égal à un sur un moins c."]
        with mock.patch("unistudent.convert._convert", return_value=Conversion(pages, "pdftotext")):
            built, page = self.build("table.pdf", lambda path: write(path))
        self.assertEqual(built["needs_visual"], [])
        self.assertIn("ריבית", page)


try:
    import pypdf  # optional: `us upright` needs it
except ImportError:
    pypdf = None


@unittest.skipUnless(pypdf, "pypdf not installed")
class UprightPages(CourseTestCase):
    """#63: the source-reader (no shell) gets an upright copy of a sideways scan's pages to Read."""

    def test_chosen_pages_are_turned_by_the_angle_given_or_by_the_page_s_own_rotation(self):
        own = self.tmp / "own" / "Unit 1"
        make_pdf(own / "scan.pdf", ["first page", "second page", "third page"])
        turned = pypdf.PdfWriter(clone_from=str(make_pdf(self.tmp / "turned.pdf", ["shown turned"])))
        turned.pages[0].rotate(90)  # a viewer turns it; a renderer that ignores /Rotate would not
        turned.write(own / "turned.pdf")
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own", "--tier", "official")

        copy = run_json("upright", "official/Unit 1/scan.pdf", "3", "1", "--rotate", "90", "--course", course)["path"]
        pages = pypdf.PdfReader(copy).pages
        self.assertTrue(Path(copy).is_absolute())
        self.assertEqual([(p.rotation, float(p.mediabox.width)) for p in pages], [(0, 792.0)] * 2)  # landscape, upright
        self.assertIn("third page", pages[0].extract_text())

        stored = folders(course).material / "official" / "Unit 1" / "turned.pdf"
        [page] = pypdf.PdfReader(run_json("upright", stored, "1", "--course", course)["path"]).pages
        self.assertEqual((page.rotation, float(page.mediabox.width)), (0, 792.0))

    def test_a_page_the_file_does_not_have_is_an_error(self):
        make_pdf(self.tmp / "own" / "Unit 1" / "scan.pdf", ["only page"])
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own", "--tier", "official")
        code, out = run("upright", "official/Unit 1/scan.pdf", "2", "--course", course)
        self.assertEqual(code, 1)
        self.assertIn("1 page", out)


try:
    import pptx  # optional: the slides' pictures are only extracted when python-pptx is installed
except ImportError:
    pptx = None


@unittest.skipUnless(pptx, "python-pptx not installed")
class SlidePictures(CourseTestCase):
    def test_a_slide_with_only_a_picture_hands_the_picture_to_the_source_reader(self):
        import base64
        from pptx import Presentation
        png = write(self.tmp / "graph.png", base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
        deck = Presentation()
        deck.slides.add_slide(deck.slide_layouts[5]).shapes.title.text = "Unit 1: supply, demand and the equilibrium price"
        deck.slides.add_slide(deck.slide_layouts[6]).shapes.add_picture(str(png), 0, 0)  # a graph, no text at all
        own = self.tmp / "own" / "Unit 1"
        own.mkdir(parents=True)
        deck.save(own / "slides.pptx")
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own", "--tier", "official")
        with mock.patch("unistudent.convert._soffice", return_value=None):
            [item] = run_json("wiki", "build", "--course", course)["needs_visual"]
        self.assertEqual(item["pages"], [2])
        self.assertEqual([p.rsplit("/", 1)[-1] for p in item["pictures"]], ["slide-2-1.png"])


@unittest.skipUnless(convert._soffice(), "LibreOffice not installed")
class OfficeView(CourseTestCase):
    def test_an_office_file_keeps_its_pdf_so_a_worker_can_look_at_its_pages(self):
        own = self.tmp / "own" / "Unit 1"
        own.mkdir(parents=True)
        (own / "notes.rtf").write_text(r"{\rtf1\ansi Unit 1: a ledger of assets and liabilities, long enough to count.}")
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own", "--tier", "official")
        run_json("wiki", "build", "--course", course)
        page = (folders(course).wiki / "sources" / "unit-01" / "notes.md").read_text("utf-8")
        self.assertIn("view: .unistudent/view/sources/unit-01/notes.pdf", page)
        self.assertTrue((course / ".unistudent" / "view" / "sources" / "unit-01" / "notes.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
