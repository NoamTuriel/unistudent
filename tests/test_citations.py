"""Ticket 16: citations in the Study vault are disk links to the student's own files, never to the hidden Wiki."""
import re
import shutil
import unittest
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import url2pathname

from helpers import CourseTestCase, folders, mock_env, run_json, write

LINK = re.compile(r"\[[^\]]*\]\((<[^>]+>|[^)\s]+)\)")


def targets(page):
    return [t.strip("<>") for t in LINK.findall(page.read_text("utf-8"))]


def disk_path(link):
    return Path(url2pathname(urlparse(link).path))


class Citations(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        own = self.tmp / "own"
        write(own / "Unit 4" / "slides נושא.txt", "money multiplier")
        write(own / "Unit 4" / "session 5.mp4", b"\x00" * 64)
        run_json("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/session 5.mp4")
        self.f = folders(self.course)
        rec = self.f.wiki / "recordings" / "session 5"
        write(rec / "toc.md", "| 00:12:47 | exam question | [00:12:47](transcript.md#001230) |\n")
        write(rec / "summary.md", "Sources: [transcript](transcript.md)\n\n## Announcements\n\nHomework due Sunday.\n")
        run_json("wiki", "build", "--course", self.course)
        self.pack = self.f.study / "Unit 4" / "Study pack.md"
        self.material = next(self.f.material.rglob("slides*"))
        self.page = next((self.f.wiki / "sources").rglob("slides*.md"))
        self.wiki_link = quote(self.page.relative_to(self.f.wiki).as_posix())

    def check(self, page=None):
        return [p["kind"] for p in run_json("check", page or self.pack, "--course", self.course)["problems"]]

    def test_roadmap_links_are_disk_links_to_existing_files_and_never_into_the_hidden_folder(self):
        roadmap = self.f.study / "Unit 4" / "Recordings roadmap.md"
        links = targets(roadmap)
        self.assertTrue(links)
        for link in links:
            self.assertTrue(link.startswith("file:"), link)
            self.assertTrue(disk_path(link).exists(), link)
            self.assertNotIn(".unistudent", link)
        self.assertIn("[00:12:47]", roadmap.read_text("utf-8"))
        self.assertEqual(self.check(roadmap), [])

    def test_check_flags_a_pack_that_links_into_the_wiki_or_at_a_deleted_file(self):
        write(self.pack, f"✅ It is 1/r. Sources: [slides](../../.unistudent/wiki/{self.wiki_link})\n")
        self.assertIn("link-into-hidden", self.check())
        write(self.pack, f"✅ It is 1/r. Sources: [slides, page 1]({self.material.as_uri()})\n")
        self.assertEqual(self.check(), [])
        self.material.unlink()
        self.assertIn("broken-link", self.check())

    def test_a_hebrew_name_and_spaces_resolve(self):
        write(self.pack, f"✅ x. Sources: [slides, page 1]({self.material.as_uri()})\n")
        self.assertTrue(disk_path(targets(self.pack)[0]).exists())

    def test_the_build_rewrites_old_wiki_links_to_the_students_file(self):
        write(self.pack, "✅ It is 1/r. Sources: [slides](../../.unistudent/wiki/"
                         f"{self.wiki_link}#page-3)\n")
        run_json("wiki", "build", "--course", self.course)
        link = targets(self.pack)[0]
        self.assertEqual(disk_path(link).resolve(), self.material.resolve())
        self.assertIn("page 3", self.pack.read_text("utf-8"))
        self.assertEqual(self.check(), [])

    def test_moving_a_file_or_the_whole_course_keeps_links_working(self):
        write(self.pack, f"✅ x. Sources: [slides, page 1]({self.material.as_uri()})\n")
        moved = self.material.parent.parent / "Elsewhere" / self.material.name
        moved.parent.mkdir()
        shutil.move(self.material, moved)
        run_json("wiki", "build", "--course", self.course)
        self.assertEqual(self.check(), [])
        new_root = self.tmp / "Moved"
        shutil.move(self.course, new_root)
        self.course = new_root
        self.f = folders(new_root)
        self.pack = self.f.study / "Unit 4" / "Study pack.md"
        run_json("wiki", "build", "--course", new_root)
        self.assertEqual(self.check(), [])

    def test_old_wiki_links_are_rewritten_when_the_course_folder_is_reached_through_a_symlink(self):
        link = self.tmp / "Link"
        try:
            link.symlink_to(self.course, target_is_directory=True)
        except OSError:
            self.skipTest("symlinks are not available here")
        write(self.pack, f"✅ x. Sources: [slides]({(link / '.unistudent' / 'wiki' / self.page.relative_to(self.f.wiki)).as_uri()})\n")
        run_json("wiki", "build", "--course", link)
        self.assertEqual(disk_path(targets(self.pack)[0]).resolve(), self.material.resolve())
        self.assertEqual(self.check(), [])


if __name__ == "__main__":
    unittest.main()
