"""Seam 1 (sync): the OpenU course site through a Saved login (ADR 0019): login form → scan → download → ingest.

A fake OpenU (SSO, Moodle pages, the video collection and the CDN redirector) runs on 127.0.0.1, shaped like the real
site as checked on 2026-11-21.
"""
import http.server
import json
import os
import shutil
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

from helpers import CourseTestCase, run, run_json
from test_recording_streams import make_video
from unistudent import openu

GOOD = {"p_user": "student", "p_sisma": "סיסמה-1234", "p_mis_student": "123456789"}
FILES = {"/pluginfile.php/1/mod_resource/content/1/notes.pdf": b"%PDF unit 1 notes",
         "/pluginfile.php/2/mod_url/content/1/ex.docx": b"exercise",
         "/pluginfile.php/3/mod_folder/content/0/exam 2025.pdf": b"%PDF exam",
         "/pluginfile.php/9/mod_ouilvideocollection/attachment/4001/class ex.pdf": b"%PDF class"}
SECTIONS = {2: "פתרונות לממנים", 3: "וידאו", 4: "סילבוס"}
COLLECTIONS = {"55": ("900", "AbCd"), "56": ("901", "EfGh")}  # cmid: (cid, mid)


class FakeOpenU(http.server.BaseHTTPRequestHandler):
    video = None  # a local video file standing in for the HLS stream

    def log_message(self, *args):
        pass

    def _send(self, status, body=b"", headers=(), head=False):
        body = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(status)
        for k, v in headers:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _redirect(self, to, cookie=None):
        self._send(303, headers=[("Location", to)] + ([("Set-Cookie", cookie)] if cookie else []))

    def _cookie(self, name):
        return f"{name}=" in (self.headers.get("Cookie") or "")

    def _form(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("ascii")
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw, encoding="windows-1255").items()}

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/process":
            form = self._form()
            if not self._cookie("cookies_enabled"):  # set by the login page: a POST without it is refused (as the real SSO)
                return self._send(200, "<html>עליך לאפשר קליטת עוגיות (cookies)</html>")
            if all(form.get(k) == v for k, v in GOOD.items()):
                return self._redirect(form["T_PLACE"], "sso=ok; Path=/")
            return self._send(200, "<html>שם משתמש או סיסמה שגויים</html>")
        if url.path == "/mod/ouilvideocollection/actions.php" and self._cookie("MoodleSession"):
            form = self._form()
            n, cm = {"4001": ("1", "55"), "4002": ("2", "56")}[form["playlistid"]]
            assert form == {"action": "getplaylist", "context": COLLECTIONS[cm][0], "playlistid": form["playlistid"],
                            "course": "7", "mid": COLLECTIONS[cm][1]}, form
            return self._send(200, json.dumps({
                "title": f"Lesson {n}", "recorddate": "10/09/2026",
                "media": {"duration": 1 + int(n), "cipher": urllib.parse.quote(f"abc{n}+/=", safe="")},
                "attachments": "" if n == "2" else f'<span class="ovc_attachment_sp"><a href="{self.base}/pluginfile.php/9/'
                                                   'mod_ouilvideocollection/attachment/4001/class%20ex.pdf">class ex</a></span>'}))
        self._send(404)

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_GET(self, head=False):
        url = urllib.parse.urlparse(self.path)
        query = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        if url.path == "/auth/ouilsso/redirect2.php":
            return self._redirect(query["urltogo"], "MoodleSession=s1; Path=/") if self._cookie("sso") else self._redirect("/login")
        if url.path == "/login":
            return self._send(200, "<form id=login_sso></form>", [("Set-Cookie", "cookies_enabled=1; Path=/")])
        if url.path.startswith("/Redirector/"):  # the CDN: no cookies needed
            return self._send(200, f'<rss><channel><item><jwplayer:source file="{self.video}" /></item></channel></rss>')
        if not self._cookie("MoodleSession"):
            return self._redirect("/login")
        if url.path == "/my/":
            return self._send(200, '<a href="/course/view.php?id=7">מבוא לפסיכולוגיה (2025א)</a>')
        if url.path == "/course/view.php" and "section" not in query:
            return self._send(200, '<h2>מבוא לפסיכולוגיה - 10101</h2>' + "".join(
                f'<li id="section-{n}"><h3 class="sectionname">{t}</h3></li>' for n, t in SECTIONS.items()))
        if url.path == "/course/view.php":
            # As on the real site: a quick-links block on every section page links one collection; the "וידאו"
            # section embeds all of them; the next section links back to one with its "previous" button.
            main = {"3": "".join(f'<a class="collection_link" href="#" cid="{c}" mid="{m}" cmid="{cm}"></a>'
                                 for cm, (c, m) in COLLECTIONS.items()),
                    "4": '<a class="sequence_navto" href="/mod/ouilvideocollection/view.php?id=56&amp;from=topPrev">prev</a>'}
            return self._send(200, '<aside data-block="ou_quick_links"><a href="/mod/ouilvideocollection/view.php?id=55">'
                              f'Recordings</a></aside><div id="region-main">{main.get(query["section"], "")}</div>')
        if url.path == "/course/resources.php":
            rows = [("יחידה 1: מבוא", "Unit 1 notes", "/mod/resource/view.php?id=101"),
                    ("", "Exercise", "/mod/url/view.php?id=102"),
                    ("מבחנים מ2025", "Exams", "/mod/folder/view.php?id=103"),
                    ("מפגשים", "Zoom", "/mod/ouilvideolive/view.php?id=104")]
            return self._send(200, '<table class="generaltable"><tbody>' + "".join(
                f'<tr><td>{s}</td><td><a href="{self.base}{h}">{n}</a></td><td></td></tr>' for s, n, h in rows)
                + "</tbody></table>")
        if url.path in ("/mod/resource/view.php", "/mod/url/view.php") and query.get("redirect") == "1":
            target = {"101": "/pluginfile.php/1/mod_resource/content/1/notes.pdf",
                      "102": "/pluginfile.php/2/mod_url/content/1/ex.docx"}[query["id"]]
            return self._redirect(target)
        if url.path == "/mod/folder/view.php":
            return self._send(200, f'<a href="{self.base}/pluginfile.php/3/mod_folder/content/0/exam%202025.pdf?forcedownload=1">exam</a>')
        if urllib.parse.unquote(url.path) in FILES:
            return self._send(200, FILES[urllib.parse.unquote(url.path)], head=head)
        if url.path == "/mod/ouilvideocollection/view.php":
            n = {"55": "1", "56": "2"}[query["id"]]
            return self._send(200, "".join(f'<a class="collection_link" href="#" c-value="1" cid="{c}" mid="{m}" cmid="{cm}" '
                                           'sort-type="1"></a>' for cm, (c, m) in COLLECTIONS.items())
                              + f'<div id="collection1"><div id="playlist400{n}"><div><span class="ovc_playlist_title" '
                              f'title="Lesson {n}" tabindex="0">Lesson {n}</span></div></div></div>')
        if url.path == "/local/ouil_video/player.php":
            assert query["mediaid"] in ("abc1+/=", "abc2+/="), query
            return self._send(200, 'var jwplayer_parameters = {"file":"' + self.base.replace("/", "\\/")
                              + '\\/Redirector\\/openu\\/c1_HD_mp4\\/hls"};')
        self._send(404)


class OpenUSite(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenU)
        base = f"http://127.0.0.1:{self.server.server_port}"
        FakeOpenU.base = base
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.patches = [mock.patch.object(openu, "SITE", base), mock.patch.object(openu, "SSO", base),
                        mock.patch.object(openu, "CDN", f"127.0.0.1:{self.server.server_port}")]
        for p in self.patches:
            p.start()
        self.course = self.tmp / "Psych"
        run("setup", self.course, "--name", "Psych", "--language", "he", "--university", "openu")
        self.downloads = self.tmp / "Downloads"

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def save_good_login(self):
        openu.save_login({"username": GOOD["p_user"], "password": GOOD["p_sisma"], "id_number": GOOD["p_mis_student"]})

    def test_the_form_saves_only_a_login_that_works_and_forget_deletes_it(self):
        pages, browser = [], []

        def student_types(url):  # the student's browser: a typo first, then the right password
            def fill():
                for password in ("wrong-pass", GOOD["p_sisma"]):
                    data = urllib.parse.urlencode({"username": "student", "password": password,
                                                   "id_number": "123456789"}).encode()
                    pages.append(urllib.request.urlopen(url, data).read().decode("utf-8"))
            browser.append(threading.Thread(target=fill, daemon=True))
            browser[0].start()
            return True

        self.assertFalse(run_json("openu", "status")["saved"])
        with mock.patch("webbrowser.open", side_effect=student_types):
            self.assertTrue(run_json("openu", "login")["saved"])
        browser[0].join(10)
        self.assertIn("didn&#x27;t accept this login", pages[0])
        self.assertIn('value="student"', pages[0])  # what was typed stays, except the password
        self.assertNotIn("wrong-pass", pages[0])
        self.assertIn("Saved", pages[1])
        path = self.home / "logins.json"
        self.assertEqual(json.loads(path.read_text("utf-8"))["openu"]["password"], GOOD["p_sisma"])
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(run_json("openu", "status")["saved"])
        self.assertTrue(run_json("openu", "forget")["forgotten"])
        self.assertFalse(run_json("openu", "status")["saved"])

    def test_a_saved_login_that_stopped_working_says_so_in_plain_words(self):
        openu.save_login({"username": "student", "password": "old", "id_number": "123456789"})
        code, out = run("openu", "scan", "--course", self.course)
        self.assertEqual(code, 1)
        self.assertIn("didn't accept the Saved login", out)

    def test_scan_lists_files_folders_recordings_and_their_attachments(self):
        self.save_good_login()
        self.assertEqual(run_json("openu", "scan", "--course", self.course)["courses"],
                         [{"id": "7", "name": "מבוא לפסיכולוגיה (2025א)"}])
        result = run_json("openu", "scan", "--course", self.course, "--course-id", "7", self.downloads)
        self.assertEqual((result["documents"], result["recordings"]), (4, 2))
        listing = json.loads(Path(result["listing"]).read_text("utf-8"))
        items = {i["name"]: i for i in listing["items"]}
        notes = items["Unit 1 notes"]
        self.assertEqual((notes["section"], notes["size"]), ("יחידה 1: מבוא", len(FILES["/pluginfile.php/1/mod_resource/content/1/notes.pdf"])))
        self.assertTrue(notes["file"].startswith("unistudent-10101-") and notes["file"].endswith("__Unit 1 notes.pdf"))
        self.assertEqual(items["Exercise"]["section"], "יחידה 1: מבוא")  # an empty section cell: the section above
        self.assertEqual(items["exam 2025.pdf"]["unit_hint"], "general")
        lesson = items["Lesson 1 10/09/2026"]
        self.assertEqual((lesson["kind"], lesson["seconds"], lesson["section"]), ("recording", 2, "וידאו"))
        # the collection that only the "וידאו" section embeds is found too, under that section
        self.assertEqual(items["Lesson 2 10/09/2026"]["section"], "וידאו")
        self.assertEqual(items["class ex.pdf"]["attached_to"], lesson["url"])
        plan = run_json("fetch-plan", "show", "--course", self.course, result["listing"])
        self.assertFalse(plan["nothing_new"])

    def test_approved_files_download_and_ingest_and_a_second_sync_finds_nothing_new(self):
        self.save_good_login()
        listing = run_json("openu", "scan", "--course", self.course, "--course-id", "7", self.downloads)["listing"]
        run_json("fetch-plan", "show", "--course", self.course, listing)
        approved = run_json("fetch-plan", "apply", "--course", self.course, listing)["listing"]
        got = run_json("openu", "download", "--course", self.course, approved, self.downloads)
        self.assertEqual((len(got["downloaded"]), got["failed"]), (4, {}))
        ingested = run_json("ingest", "--course", self.course, "--no-wiki", approved, self.downloads)
        self.assertEqual((len(ingested["new"]), ingested["missing"]), (4, []))
        again = run_json("openu", "scan", "--course", self.course, "--course-id", "7", self.tmp / "again")["listing"]
        self.assertEqual(run_json("openu", "download", "--course", self.course, again, self.tmp / "again")["downloaded"], [])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
    def test_an_approved_recording_streams_and_ingests(self):
        FakeOpenU.video = make_video(self.tmp / "cdn" / "lesson.mp4")
        self.save_good_login()
        listing = run_json("openu", "scan", "--course", self.course, "--course-id", "7", self.downloads)["listing"]
        run_json("fetch-plan", "show", "--course", self.course, listing)
        approved = run_json("fetch-plan", "apply", "--course", self.course, listing)["listing"]
        url = next(i["url"] for i in json.loads(Path(approved).read_text("utf-8"))["items"] if i["kind"] == "recording")
        got = run_json("openu", "stream", "--course", self.course, approved, self.downloads, "--url", url)
        self.assertEqual(len(got["downloaded"]), 1)
        ingested = run_json("ingest", "--course", self.course, "--no-wiki", got["listing"], self.downloads)
        self.assertEqual(len(ingested["new"]), 1)
        self.assertTrue(ingested["new"][0].endswith(".mp4"))


if __name__ == "__main__":
    unittest.main()
