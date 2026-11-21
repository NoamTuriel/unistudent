"""The Open University of Israel course site over plain HTTP, from the student's Saved login (ADR 0019).

The same scan and downloads the OpenU sync skill otherwise runs as scripts in the student's Chrome
(plugins/openu/skills/openu-sync/references/site.md): log in through the OU SSO, list the course's files and
recordings into a listing, download the approved files, and collect one recording's stream link right before
its download.
"""
import datetime
import hashlib
import html
import http.server
import json
import os
import re
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.cookiejar import CookieJar
from pathlib import Path

from .common import UserError
from .course import home, safe_name

SITE = "https://opal.openu.ac.il"
SSO = "https://sso.apps.openu.ac.il"
CDN = "apiou.bynetcdn.com"  # the player's redirector: answers with the stream link, no cookies needed
FIELDS = {"username": "p_user", "password": "p_sisma", "id_number": "p_mis_student"}
GENERAL = re.compile(r"בחינ|מבחנ|מחסן קבצים")  # past exams, exam information, file stores: whole-course
TIMEOUT = 60


# --- the Saved login ----------------------------------------------------------

def logins_file() -> Path:
    return home() / "logins.json"


def saved_login():
    path = logins_file()
    return json.loads(path.read_text("utf-8")).get("openu") if path.exists() else None


def _write_logins(data):
    path = logins_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # readable by the student only
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.chmod(path, 0o600)  # an older file keeps its mode through O_TRUNC


def save_login(login):
    path = logins_file()
    _write_logins({**(json.loads(path.read_text("utf-8")) if path.exists() else {}), "openu": login})


def forget_login():
    path = logins_file()
    data = json.loads(path.read_text("utf-8")) if path.exists() else {}
    if data.pop("openu", None) is None:
        return False
    _write_logins(data)
    return True


# --- logging in -------------------------------------------------------------

class LoginRefused(UserError):
    """The site answered, and didn't take the login."""


def login(creds):
    """A URL opener logged in to the course site, or UserError when the site doesn't take the login."""
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (UniStudent)")]
    form = {FIELDS[k]: creds.get(k, "") for k in FIELDS}
    form["T_PLACE"] = f"{SITE}/auth/ouilsso/redirect2.php?urltogo={SITE}/my/"
    data = urllib.parse.urlencode(form, encoding="windows-1255", errors="replace").encode()  # the SSO page's charset
    try:
        # The login page sets the cookie the SSO checks: a POST without it gets "allow cookies" and no login.
        opener.open(f"{SSO}/login?" + urllib.parse.urlencode({"T_PLACE": form["T_PLACE"]}), timeout=TIMEOUT).read()
        opener.open(urllib.request.Request(f"{SSO}/process", data), timeout=TIMEOUT).read()
        reply = opener.open(f"{SITE}/my/", timeout=TIMEOUT)
        reply.read()
    except OSError as error:
        raise UserError(f"Couldn't reach the OpenU site ({error}). Check the internet connection and try again.")
    if not reply.geturl().startswith(f"{SITE}/my"):
        raise LoginRefused("The OpenU site didn't accept the Saved login (a changed password, or a typo). "
                        "Run `us openu login` to type it again, or sync through Chrome this time.")
    return opener


def session():
    creds = saved_login()
    if not creds:
        raise UserError("No Saved login for OpenU yet: run `us openu login`, or sync through Chrome.")
    return login(creds)


def _get(opener, url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    with opener.open(urllib.request.Request(url, body), timeout=TIMEOUT) as reply:
        charset = reply.headers.get_content_charset() or "utf-8"
        return reply.read().decode(charset, "replace")


FORM = """<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>UniStudent: OpenU login</title>
<style>body{{font:16px system-ui,sans-serif;max-width:26rem;margin:2rem auto;padding:0 1rem}}
label{{display:block;margin:.8rem 0 .2rem}}input{{width:100%;padding:.5rem;font:inherit;box-sizing:border-box}}
button{{margin-top:1.2rem;padding:.6rem 1.2rem;font:inherit}}.e{{color:#b00}}p{{color:#555}}</style>
<h1>כניסה לאתר האו"פ / OpenU login</h1>
<p>Saved on this computer only (in {path}), readable only by you. UniStudent uses it to log in to the course site
for you. The AI never sees it. To delete it: <code>us openu forget</code>.</p>{error}
<form method="post" action="/{token}">
<label>שם משתמש/ת / Username<input name="username" required autocomplete="username" value="{username}"></label>
<label>סיסמה / Password<input name="password" type="password" required autocomplete="current-password"></label>
<label>מספר זהות / ID number<input name="id_number" required inputmode="numeric" pattern="[0-9]{{9}}" value="{id_number}"></label>
<button>Save</button></form></html>"""
DONE = """<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8"><title>Saved</title>
<body style="font:16px system-ui,sans-serif;max-width:26rem;margin:2rem auto">
<h1>נשמר / Saved</h1><p>The login works and is saved. You can close this tab and go back to the chat.</p></html>"""


def ask_for_login(wait_seconds=600):
    """Serve a one-time form on 127.0.0.1, check what the student types by logging in, save it, and return True.
    False when the form wasn't sent in time. The password goes from the browser to this process only."""
    token = secrets.token_urlsafe(16)
    state = {"saved": False}

    class Form(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _page(self, body, status=200):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _form(self, error="", typed=None):
            typed = typed or {}
            return FORM.format(path=html.escape(str(logins_file())), token=token,
                               error=f'<p class="e">{html.escape(error)}</p>' if error else "",
                               username=html.escape(typed.get("username", "")),
                               id_number=html.escape(typed.get("id_number", "")))

        def do_GET(self):
            if self.path != f"/{token}":
                return self._page("Not found", 404)
            self._page(self._form())

        def do_POST(self):
            if self.path != f"/{token}":
                return self._page("Not found", 404)
            length = int(self.headers.get("Content-Length") or 0)
            typed = {k: v[0].strip() for k, v in urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8")).items()}
            creds = {k: typed.get(k, "") for k in FIELDS}
            try:
                login(creds)
            except LoginRefused:
                return self._page(self._form("OpenU didn't accept this login. Check the three fields and try again.", typed))
            except UserError as error:
                return self._page(self._form(str(error), typed))
            save_login(creds)
            state["saved"] = True
            self._page(DONE)

    server = http.server.HTTPServer(("127.0.0.1", 0), Form)
    url = f"http://127.0.0.1:{server.server_port}/{token}"
    try:
        print(f"The login form is at {url} (open it on this computer if no tab opened).", file=sys.stderr, flush=True)
        if not webbrowser.open(url):
            raise UserError(f"Couldn't open a browser. Open this address on this computer: {url}")
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=wait_seconds)
        server.timeout = 1
        while not state["saved"] and datetime.datetime.now() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    return state["saved"]


# --- scanning ---------------------------------------------------------------

def _text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _absolute(href):
    return urllib.parse.urljoin(SITE + "/", html.unescape(href))


def courses(opener):
    """[{id, name}] of the student's courses, as /my/ lists them ("<name> (<semester>)")."""
    page = _get(opener, f"{SITE}/my/")
    found = {}
    for href, inner in re.findall(r'<a[^>]+href="([^"]*/course/view\.php\?id=(?:\d+))"[^>]*>(.*?)</a>', page, re.S):
        course_id = re.search(r"id=(\d+)", href).group(1)
        name = _text(inner)
        if name and course_id not in found:
            found[course_id] = name
    return [{"id": k, "name": v} for k, v in found.items()]


def _resource_rows(opener, course_id):
    page = _get(opener, f"{SITE}/course/resources.php?id={course_id}")
    table = re.search(r'<table[^>]*class="[^"]*generaltable[^"]*".*?</table>', page, re.S)
    rows, section = [], ""
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", table.group(0) if table else "", re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 2:
            continue
        section = _text(cells[0]) or section  # an empty section cell belongs to the section above
        link = re.search(r'href="([^"]*/mod/(resource|url|folder)/view\.php\?id=\d+)"', row)
        if link:  # other types (e.g. ouilvideolive, a Zoom page) hold no file
            url = _absolute(link.group(1))
            rows.append({"section": section, "name": _text(cells[1]), "type": link.group(2),
                         "url": url if link.group(2) == "folder" else url + "&redirect=1"})
    return rows


def _folder_files(opener, folder_url):
    page = _get(opener, folder_url)
    files = {}
    for href in re.findall(r'href="([^"]*/pluginfile\.php/[^"]*/mod_folder/content/[^"]*)"', page):
        url = _absolute(href).split("?")[0]
        files.setdefault(url, urllib.parse.unquote(url.rsplit("/", 1)[-1]))
    return files


def _sections(page):
    """{number: title} of the course page's sections (tiles)."""
    found = {}
    for match in re.finditer(r'id="section-(\d+)"', page):
        title = re.search(r'<(?:h3|h4)[^>]*>(.*?)</(?:h3|h4)>|class="[^"]*sectionname[^"]*"[^>]*>(.*?)</',
                          page[match.end():match.end() + 4000], re.S)
        found[int(match.group(1))] = _text(title.group(1) or title.group(2)) if title else ""
    return found


def _collections(opener, course_id, course_page):
    """[(collection URL, section title)]: the video collections linked from the course's section pages."""
    sections = _sections(course_page)
    found = {}
    for number in sorted({0, *sections}):
        page = _get(opener, f"{SITE}/course/view.php?id={course_id}&section={number}")
        for cm in re.findall(r"/mod/ouilvideocollection/view\.php\?id=(\d+)", page):
            found.setdefault(f"{SITE}/mod/ouilvideocollection/view.php?id={cm}", sections.get(number, ""))
    return list(found.items())


def _attr(tag, name):
    match = re.search(rf'\s{name}="([^"]*)"', tag)
    return html.unescape(match.group(1)) if match else None


def _recordings(opener, course_id, collection_url):
    """One dict per recording in a collection: its title, date, length, attachments and what `stream` needs."""
    page = _get(opener, collection_url)
    cm = re.search(r"id=(\d+)", collection_url).group(1)
    link = next((t for t in re.findall(r"<a[^>]*collection_link[^>]*>", page) if _attr(t, "cmid") == cm), None)
    if not link:
        return []
    found = []
    for match in re.finditer(r'id="playlist(\d+)"', page):
        title = re.search(r'class="[^"]*ovc_playlist_title[^"]*"[^>]*>(.*?)</', page[match.end():match.end() + 3000], re.S)
        media = {"collection": collection_url, "context": _attr(link, "cid"), "mid": _attr(link, "mid"),
                 "playlist": match.group(1), "course": course_id}
        info = json.loads(_get(opener, f"{SITE}/mod/ouilvideocollection/actions.php", {
            "action": "getplaylist", "context": media["context"], "playlistid": media["playlist"],
            "course": course_id, "mid": media["mid"]}))
        found.append({"title": _text(title.group(1)) if title else _text(info.get("title", "")),
                      "date": info.get("recorddate", ""),
                      "seconds": (info.get("media") or {}).get("duration"),
                      "attachments": [_absolute(h) for h in re.findall(r'href="([^"]+)"', info.get("attachments") or "")
                                      if "/attachment/" in h],
                      "media": media})
    return found


def _size_and_type(opener, item, prefix):
    """The file's size and real type from its headers only (nothing downloads); sets `size` and `file`."""
    ext = ""
    try:
        with opener.open(urllib.request.Request(item["url"], method="HEAD"), timeout=TIMEOUT) as reply:
            if reply.headers.get("Content-Length"):
                item["size"] = int(reply.headers["Content-Length"])
            ext = (re.search(r"\.[A-Za-z0-9]+$", urllib.parse.unquote(urllib.parse.urlparse(reply.geturl()).path))
                   or [""])[0]
    except OSError:
        pass  # a link to another site: no size
    item["file"] = prefix + re.sub(r'[\\/:*?"<>|]', "-", item["name"]) + ext


def scan(opener, course_id, folder, recordings=True):
    """Write the listing of everything on the course site (the Fetch plan leaves out what's already downloaded) as
    `unistudent-<course number>-<date>__listing.json` in `folder`. Returns (path, counts)."""
    course_page = _get(opener, f"{SITE}/course/view.php?id={course_id}")
    number = re.search(r"-\s*(\d{4,6})\s*<", course_page)
    prefix = f"unistudent-{number.group(1) if number else course_id}-{datetime.date.today().isoformat()}__"
    items = []
    for row in _resource_rows(opener, course_id):
        hint = {"unit_hint": "general"} if GENERAL.search(row["section"]) else {}
        if row["type"] == "folder":
            for url, name in _folder_files(opener, row["url"]).items():
                items.append({"url": url, "name": name, "section": row["section"], "kind": "document", **hint})
        else:
            items.append({"url": row["url"], "name": row["name"], "section": row["section"], "kind": "document", **hint})
    skipped = 0
    for collection_url, section in _collections(opener, course_id, course_page):
        for rec in _recordings(opener, course_id, collection_url):
            url = f"{collection_url}#{rec['title']}"
            for attachment in rec["attachments"]:  # files the lecturer hung on a recording are in no other list
                items.append({"url": attachment, "name": urllib.parse.unquote(attachment.rsplit("/", 1)[-1]),
                              "section": rec["title"], "kind": "document", "attached_to": url})
            if not recordings:
                skipped += 1
                continue
            items.append({"url": url, "title": rec["title"], "name": f"{rec['title']} {rec['date']}".strip(),
                          "section": section, "kind": "recording", "media": rec["media"],
                          **({"seconds": rec["seconds"]} if rec["seconds"] else {})})
    for item in items:
        if item["kind"] == "document":
            _size_and_type(opener, item, prefix)
    path = Path(folder) / f"{prefix}listing.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"course_site": f"{SITE}/course/view.php?id={course_id}", "items": items},
                               ensure_ascii=False, indent=1), "utf-8")
    return path, {"documents": sum(i["kind"] == "document" for i in items),
                  "recordings": sum(i["kind"] == "recording" for i in items), "recordings_skipped": skipped}


# --- downloading ------------------------------------------------------------

def _download(opener, url, target):
    part = target.with_name(target.name + ".part")
    with opener.open(url, timeout=TIMEOUT) as reply, open(part, "wb") as out:
        while chunk := reply.read(1 << 20):
            out.write(chunk)
    os.replace(part, target)


def download(opener, listing, folder, have=()):
    """Download every document of an approved listing not downloaded before into `folder`, under its `file` name.
    A failure is retried once, then reported."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    done, failed = [], {}
    for item in json.loads(Path(listing).read_text("utf-8")).get("items", []):
        if item.get("kind") == "recording" or item.get("url") in have or not item.get("file"):
            continue
        target = folder / item["file"]
        if target.exists():
            continue  # a resumed run
        for attempt in (1, 2):
            try:
                _download(opener, item["url"], target)
                done.append(item["file"])
                break
            except OSError as error:
                if attempt == 2:
                    failed[item["file"]] = str(error)
    return done, failed


def stream_url(opener, media):
    """A recording's stream link (HLS, with a token valid for a few hours): the player's token from the collection,
    the player's CDN redirector link from the player page, and the stream from the redirector (no cookies needed)."""
    info = json.loads(_get(opener, f"{SITE}/mod/ouilvideocollection/actions.php", {
        "action": "getplaylist", "context": media["context"], "playlistid": media["playlist"],
        "course": media["course"], "mid": media["mid"]}))
    cipher = urllib.parse.unquote((info.get("media") or {}).get("cipher") or "")
    if not cipher:
        raise UserError("The recording has no player link on the site (it may have been removed).")
    player = _get(opener, f"{SITE}/local/ouil_video/player.php?" + urllib.parse.urlencode({"mediaid": cipher}))
    redirector = re.search(r'https?:\\?/\\?/' + re.escape(CDN) + r'[^"\'\s]+', player)
    if not redirector:
        raise UserError("The recording's player page has no stream link.")
    with urllib.request.urlopen(redirector.group(0).replace("\\/", "/"), timeout=TIMEOUT) as reply:
        feed = reply.read().decode("utf-8", "replace")
    source = re.search(r'<jwplayer:source[^>]*\sfile="([^"]+)"', feed)
    if not source:
        raise UserError("The video server gave no stream link for the recording.")
    return html.unescape(source.group(1))


def one_recording_listing(listing, url, folder, opener):
    """Write the listing of one approved recording with its fresh stream link next to the downloads, for
    `us recordings fetch` and `us ingest`. Returns its path."""
    item = next((i for i in json.loads(Path(listing).read_text("utf-8")).get("items", [])
                 if i.get("url") == url and i.get("kind") == "recording"), None)
    if item is None or not item.get("media"):
        raise UserError(f"No recording with this url in the approved listing: {url}")
    path = Path(folder) / f"rec-{hashlib.sha1(url.encode('utf-8')).hexdigest()[:10]}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"items": [{**item, "stream_url": stream_url(opener, item["media"])}]},
                               ensure_ascii=False, indent=1), "utf-8")
    return path

