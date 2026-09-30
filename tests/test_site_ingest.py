"""Seam 1 (sync): a university plugin's listing + downloaded files → Raw, Manifest, units, "what's new".

The university plugin (e.g. openu) owns reaching the site. It hands the core a listing
(what's on the course site) and a folder of downloaded files; the core does the rest.
"""
import json
import unittest

from helpers import CourseTestCase, can_read_pdfs, make_pdf, run, run_json, write


def listing(*items):
    return {"course_site": "https://example.edu/course/123", "items": list(items)}


class SiteIngest(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--university", "openu")
        self.staged = self.tmp / "staged"

    def ingest(self, data):
        path = write(self.tmp / "listing.json", json.dumps(data))
        return run_json("ingest", "--course", self.course, path, self.staged)

    def test_downloaded_files_land_in_raw_with_site_origin_and_units(self):
        make_pdf(self.staged / "slides-u4.pdf", ["Unit 4 slides"])
        make_pdf(self.staged / "exam-2024.pdf", ["Exam"])
        result = self.ingest(listing(
            {"url": "https://example.edu/f/1", "file": "slides-u4.pdf", "name": "Unit slides.pdf",
             "section": "Unit 4 - money supply"},
            {"url": "https://example.edu/f/2", "file": "exam-2024.pdf", "name": "Exam 2024.pdf",
             "section": "Past exams", "unit_hint": "general"},
        ))
        self.assertEqual(sorted(result["new"]), ["site/Past exams/Exam 2024.pdf", "site/Unit 4 - money supply/Unit slides.pdf"])
        files = run_json("manifest", "--course", self.course)["files"]
        slides = files["site/Unit 4 - money supply/Unit slides.pdf"]
        self.assertEqual((slides["origin"], slides["tier"], slides["unit"]), ("course-site", "official", 4))
        self.assertEqual(slides["site_url"], "https://example.edu/f/1")
        self.assertEqual(files["site/Past exams/Exam 2024.pdf"]["unit"], "general")
        self.assertTrue((self.course / "raw" / "site" / "Unit 4 - money supply" / "Unit slides.pdf").is_file())
        self.assertFalse((self.staged / "slides-u4.pdf").exists())  # moved, not copied

    def test_status_tells_the_fetcher_what_is_already_downloaded(self):
        make_pdf(self.staged / "a.pdf", ["Unit 1"])
        self.ingest(listing({"url": "https://example.edu/f/1", "file": "a.pdf", "name": "a.pdf", "section": "Unit 1"}))
        status = run_json("site-status", "--course", self.course)
        self.assertEqual(status["downloaded"], ["https://example.edu/f/1"])

    def test_a_second_sync_reports_only_what_changed(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        make_pdf(self.staged / "a.pdf", ["Unit 1 v1"])
        self.ingest(listing({"url": "https://example.edu/f/1", "file": "a.pdf", "name": "a.pdf", "section": "Unit 1"}))

        make_pdf(self.staged / "a.pdf", ["Unit 1 v2 corrected"])
        make_pdf(self.staged / "b.pdf", ["Unit 2"])
        result = self.ingest(listing(
            {"url": "https://example.edu/f/1", "file": "a.pdf", "name": "a.pdf", "section": "Unit 1"},
            {"url": "https://example.edu/f/2", "file": "b.pdf", "name": "b.pdf", "section": "Unit 2"},
        ))
        self.assertEqual(result["new"], ["site/Unit 2/b.pdf"])
        self.assertEqual(result["changed"], ["site/Unit 1/a.pdf"])
        self.assertIn("Unit 1 v2", (self.course / "wiki" / "sources" / "unit-01" / "a.md").read_text("utf-8"))

    def test_items_listed_but_not_downloaded_are_reported_missing(self):
        result = self.ingest(listing({"url": "https://example.edu/f/9", "file": "gone.pdf", "name": "gone.pdf",
                                      "section": "Unit 3"}))
        self.assertEqual(result["missing"], ["https://example.edu/f/9"])
        self.assertEqual(result["new"], [])

    def test_recordings_in_the_listing_are_not_ingested_without_a_file(self):
        result = self.ingest(listing({"url": "https://example.edu/v/1", "name": "Session 1.mp4",
                                      "section": "Recordings", "kind": "recording"}))
        self.assertEqual(result["recordings_available"], ["https://example.edu/v/1"])
        self.assertEqual(result["missing"], [])


if __name__ == "__main__":
    unittest.main()
