# Open University course site: how the sync skill reaches it

Verified on 2026-09-30 in a logged-in Chrome session (ticket 01). Moodle with the OU "Smart Opal" theme; the course page itself is a tile view, so read the lists below instead of the course page.

## Courses

- `https://opal.openu.ac.il/my/` lists the student's courses as links to `/course/view.php?id=<courseid>`. The link text is "<course name> (<semester>)", e.g. "מבוא לפסיכולוגיה (2025א)". The course page header shows the course number (e.g. 10101).

## Files: one list for the whole course

`/course/resources.php?id=<courseid>` is a table (`table.generaltable`) with one row per file-like activity: section title · name · description. A row with an empty section cell belongs to the section above it. Activity types seen: `resource` (a file), `url` (usually a link to a file on the same site), `folder`.

- **resource / url:** `/mod/<type>/view.php?id=<id>&redirect=1` answers with the file itself (it redirects to `/pluginfile.php/...`). The final URL's last path part is the file name.
- **folder:** `/mod/folder/view.php?id=<id>` lists its files as `/pluginfile.php/...` links inside the main region.
- **Section titles** carry the unit: "יחידה 5: הכסף ומערכת הבנקאות". A section spanning units ("יחידות 6 ו-7") is left for the student to sort. Past-exam and "מחסן קבצים" sections are whole-course (`unit_hint: "general"`).
- Not in this list: `oufcard` (video cards, e.g. exam solutions) and video collections. Find them by opening each section tile from the course page and reading the "ניווט" block's links.

Listing snippet (run in the course tab with the javascript tool):

```js
const d = new DOMParser().parseFromString(await (await fetch('/course/resources.php?id=' + COURSE_ID, {credentials: 'include'})).text(), 'text/html');
let section = '';
window.ROWS = [...d.querySelectorAll('table.generaltable tbody tr')].map(r => {
  const cells = [...r.cells].map(c => c.textContent.trim().replace(/\s+/g, ' '));
  if (cells[0]) section = cells[0];
  const a = r.querySelector('a[href*="/mod/"]');
  const type = a && new URL(a.href).pathname.split('/')[2];
  if (!['resource', 'url', 'folder'].includes(type)) return null;  // e.g. ouilvideolive: a Zoom join page, no file
  return {section, name: cells[1], type, url: type === 'folder' ? a.href : a.href + '&redirect=1'};
}).filter(Boolean);
ROWS.length
```

The rows' links are `view.php?id=N`; only with `&redirect=1` does a request reach the file. Keep the rows in a page
variable and return counts, not the rows: the javascript tool cuts long results short and hides any result that holds a
URL with a query string.

Size and type snippet (same tab; `ITEMS` is the document items built so far, folder files included, `PREFIX` the batch prefix `unistudent-<course number>-<date>__`). It asks for each file's headers only, so nothing downloads. The final URL after the redirect names the real file, so it also gives each item its `file`, the name to download under, ending in the real file type: site titles never carry one ("הבחינה מה4.2.21"), and the core reads the type from `file`.

```js
for (const i of ITEMS) {
  try {
    const r = await fetch(i.url, {method: 'HEAD', credentials: 'include'});
    const n = r.ok && r.headers.get('content-length');
    if (n) i.size = Number(n);
    const ext = decodeURIComponent(new URL(r.url).pathname).match(/\.[A-Za-z0-9]+$/)?.[0] || '';
    i.file = PREFIX + i.name.replace(/[\/\\:*?"<>|]/g, '-') + ext;
  } catch (e) {}
}
[ITEMS.length, ITEMS.filter(i => i.size).length, ITEMS.filter(i => !/\.\w+$/.test(i.file || '')).length].join(' ')
```

It returns three counts: items, items with a size, items with no file type. Verified on 2026-10-20 (83 files): with `&redirect=1` every file answers `HEAD` with its `Content-Length`; without it the answer is an HTML page. A `url` activity that points to another site has no size.

## Downloading files

The session cookie is http-only, so scripts can't reuse it. Download from inside the logged-in tab: `fetch(url, {credentials: 'include'})` → `blob` → a temporary `<a download="<name>">` click. Files land in the student's Downloads folder (verified). Chrome may ask once to allow multiple downloads from opal.openu.ac.il: the student approves it.

Put the files in one batch folder by prefixing names, e.g. `unistudent-<course>-<date>__<name>`, and write the listing as a JSON download the same way: `new Blob([JSON.stringify(LISTING)], {type: 'application/json'})` → `URL.createObjectURL` → the same `<a download>` click.

## Recordings

- Video collections: linked as `/mod/ouilvideocollection/view.php?id=<cmid>`. Each recording is a `.ovc_playlist_title` element (title) inside `.ovc_playlist`; the date and lecturer are next to it.
- Clicking a title loads an iframe `/local/ouil_video/player.php?mediaid=<id>`. In that iframe, `jwplayer_parameters.file` is an HLS playlist on `souvod1.bynetcdn.com` with a time-limited token in the URL. It needs **no cookies**: ffmpeg can download it directly while the token is valid (a few hours). A whole course takes longer than that to download, so a link is collected only after the student's OK, one recording at a time, just before its download.
- Two quality variants: about 1.8 Mbit/s and 0.4 Mbit/s. At 1.8 Mbit/s an hour is about 0.81 GB, so a three-hour session is about 2.4 GB; far less at low quality or audio only, which is all transcription needs. The Fetch plan estimates a recording's size from its length at 1.8 Mbit/s.

Recordings snippet (scan, in the collection tab; collects no links). The page shows each title with its lecturer and date ("תאריך הקלטה: 10/09/2026") but no length (checked 2026-10-20), so the snippet opens each recording in the player and reads its length there; the player's link stays in the page. About 4 seconds per recording: run it in batches of 6 or so, the javascript tool gives up after 45 seconds.

```js
const T = [...document.querySelectorAll('.ovc_playlist_title')];
window.RECS ||= [];
for (let n = window.RECS.length; n < Math.min(T.length, window.RECS.length + 6); n++) {
  const before = document.querySelector('iframe')?.contentWindow?.jwplayer_parameters?.file;
  T[n].click();
  let seconds = 0;
  for (let k = 0; k < 20 && !seconds; k++) {
    await new Promise(r => setTimeout(r, 500));
    const w = document.querySelector('iframe')?.contentWindow;
    try { if (w.jwplayer_parameters.file !== before) seconds = Math.round(w.jwplayer().getDuration()); } catch (e) {}
  }
  const attachments = [...new Set([...document.querySelectorAll('.ovc_info_row a[href*="attachment"]')].map(a => a.href))];
  window.RECS.push({title: T[n].textContent.trim(), around: T[n].parentElement.textContent.trim().replace(/\s+/g, ' '),
                    seconds: seconds || undefined, attachments});
}
window.RECS.length + ' of ' + T.length
```

Run it again until it says all of them, then read `window.RECS` (titles, `around`, `seconds`, `attachments`; no stream links in it). `attachments` are files the lecturer hung on that recording (`/pluginfile.php/.../mod_ouilvideocollection/attachment/...`): checked 2026-10-20, 6 of 18 recordings had one, among them the class exercise file and the exam-prep file. They are in no other list on the site. Each is a document item (its `section` is the recording's title, its `attached_to` the recording's `url`; size and type from the size snippet). Read the date from `around`; `seconds` 0 or missing means the player didn't load: leave it out, and the Fetch plan shows that recording as "size unknown".

Stream snippet (download, in the collection tab; only after the student's OK, one recording per run; `ITEM` is that recording's item copied exactly from the approved listing, so it keeps `"transcribe": true`; `FILE` the one-recording listing's name). Right after the click the player first holds a placeholder link (`apiou.bynetcdn.com/.../hls`, which refuses connections) and only seconds later the real `.m3u8`: the snippet waits for it.

```js
const t = [...document.querySelectorAll('.ovc_playlist_title')].find(e => e.textContent.trim() === ITEM.title);
if (!t) throw new Error('recording no longer on the site');
const before = document.querySelector('iframe')?.contentWindow?.jwplayer_parameters?.file;
t.click();
let stream_url;
for (let k = 0; k < 40 && !stream_url; k++) {
  await new Promise(r => setTimeout(r, 500));
  const f = document.querySelector('iframe')?.contentWindow?.jwplayer_parameters?.file;
  if (f && f !== before && f.includes('.m3u8')) stream_url = f;
}
if (!stream_url) throw new Error('no stream link after 20 seconds');
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([JSON.stringify({items: [{...ITEM, stream_url}]})], {type: 'application/json'}));
a.download = FILE; a.click();
'saved'
```

The javascript tool hides tokenised URLs from Claude's view, so the snippet writes the link straight into the one-recording listing instead of returning it. `us recordings fetch` downloads from that file. Chrome never overwrites a download: a second try saved under the same name lands as `<name> (1).json`, so a retry gets its own name (`__rec-<n>-again.json`). Measured 2026-10-20: about 4 MB/s, so an hour of video (0.8 GB) takes about 3 to 4 minutes.

## Over plain HTTP, with a Saved login

What `us openu` (the core's `openu.py`) does instead of the snippets above. Checked 2026-11-21 against the live site.

- **Login:** `https://opal.openu.ac.il/login/index.php` redirects to the OU SSO, a plain HTML form (`windows-1255`) posted to `https://sso.apps.openu.ac.il/process`: `p_user` (username), `p_sisma` (password), `p_mis_student` (9-digit ID number) and `T_PLACE` (where to go after: `https://opal.openu.ac.il/auth/ouilsso/redirect2.php?urltogo=...`). No captcha and no second step. After it, `/my/` answers on opal instead of redirecting to the SSO.
- **Courses:** `/my/` links to every course; the course page header reads "<course name> - <course number>".
- **Files:** `resources.php` and folder pages are server-rendered: the same table and `pluginfile.php` links as above.
- **Video collections:** the course page has an element `id="section-<n>"` per section tile, with its title in an `h3`/`h4`. Each section page (`/course/view.php?id=<courseid>&section=<n>`) shows its collections in its main region (after `id="region-main"`): as links `/mod/ouilvideocollection/view.php?id=<cmid>` (not `?c=`), or embedded, as one `a.collection_link` per collection with its `cmid` (the "וידאו" section embeds them all: checked 2026-11-21, four collections, 70 recordings). The quick-links block above the main region, the same on every page, links only one collection, so it can't name a collection's section. "Previous"/"next" buttons link collections as `...?id=<cmid>&from=...`: not a section's own.
- **Recordings:** the collection page lists each recording as `div#playlist<N>` holding its `.ovc_playlist_title`, and the collection itself as `a.collection_link` with attributes `cid`, `mid` and `cmid` (the one whose `cmid` is this collection). A POST to `/mod/ouilvideocollection/actions.php` with `action=getplaylist&context=<cid>&playlistid=<N>&course=<courseid>&mid=<mid>` (no sesskey) answers JSON: `title`, `recorddate` (dd/mm/yyyy), `media.duration` (seconds), `attachments` (HTML with the attachment links), and `media.cipher`, the player's token, URL-encoded.
- **Stream link:** `/local/ouil_video/player.php?mediaid=<cipher, decoded>` holds, in `jwplayer_parameters`, a redirector link on `apiou.bynetcdn.com/Redirector/.../hls`. Fetched without cookies, that link answers an RSS feed whose `<jwplayer:source file="...">` is the tokenised `souvod1.bynetcdn.com/.../playlist.m3u8` that ffmpeg downloads.

## Assignments: due date and status

With a Saved login the core's `openu.py` reads them itself (`us openu scan` lists them as `kind: "assignment"` items, `download` being the assignment's file): the same pages and labels as below, read from the server's HTML, one text line per element.

Verified 2026-11-21 on the live site (a logged-in session, 4 courses with assignments, 9 assignments). The core finds open assignments from listing items that carry `kind: "assignment"`, `due` (`YYYY-MM-DD`) and `status` (`open`, `submitted`, `graded`, `unknown`); `us ingest` keeps them current on every sync.

OPAL does not use Moodle's own assignment module (`/mod/assign/` is empty). Assignments are a site module, `ouilassign` ("מטלות הקורס"), and the resources list above does not show them:

- **Index:** `/mod/ouilassign/index.php?id=<courseid>` links one page per assignment, `/mod/ouilassign/view.php?id=<id>`, titled "מטלת קובץ 01", "מטלת קובץ 02"... (a course with none has no links; the course's resources list may also hold plain files such as "פתרון מטלה 1": those are ordinary documents, not assignments). The index page also links the site's guide pages for the assignments system ("דפי הדרכה למערכת מטלות החדשה"), and a course's resources list can hold a "הגשת מטלות תלמידים" file: both are official sources for the submission steps.
- **Page (label, then its value on the next text line):** "תאריך אחרון להגשה" gives the due date as `DD/MM/YYYY` (no time on the pages seen); "משקל המטלה" the weight; "קבצים מותרים" the allowed file types. Under "ההגשה שלי": "מטלה זו טרם הוגשה" when nothing was submitted; otherwise "תאריך הגשה" (`DD/MM/YYYY HH:MM`), "מספר אסמכתא", and "סטטוס" with its value ("נבדק" = checked and graded, seen; other values for a submission not yet checked were not seen: any other value is taken as submitted). "ציון" is the grade.
- **Files:** under "המטלה" the assignment's own file (usually `.docx`): `/pluginfile.php/<n>/ouilassigntype_file/assignfile/<n>/<file>`. Under "קבצים שהוגשו" is the student's own submission, which is theirs, not course material: never ingest it.
- The student submits on the page ("הגשת המטלה": upload or update a file). The sync never touches it.

Snippet (run in the course tab, once per course; keep the result in the page variable and return counts, as above):

```js
window.ASSIGN = [];
const idx = new DOMParser().parseFromString(await (await fetch('/mod/ouilassign/index.php?id=' + COURSE_ID, {credentials: 'include'})).text(), 'text/html');
for (const href of new Set([...idx.querySelectorAll('a[href*="/mod/ouilassign/view.php"]')].map(a => a.getAttribute('href')))) {
  const d = new DOMParser().parseFromString(await (await fetch(href, {credentials: 'include'})).text(), 'text/html');
  const lines = (d.querySelector('[role=main], #region-main, main') || d.body).textContent.split('\n').map(s => s.trim()).filter(Boolean);
  const after = l => { const i = lines.indexOf(l); return i >= 0 ? lines[i + 1] : null; };
  const m = (after('תאריך אחרון להגשה') || '').match(/^(\d\d)\/(\d\d)\/(\d{4})$/);
  const state = after('סטטוס'), file = d.querySelector('a[href*="ouilassigntype_file/assignfile"]');
  ASSIGN.push({url: new URL(href, location.origin).href, name: lines.find(s => /^מטלת \S+ \d+$/.test(s)), section: 'מטלות', kind: 'assignment',
    due: m ? `${m[3]}-${m[2]}-${m[1]}` : undefined,
    status: lines.includes('מטלה זו טרם הוגשה') ? 'open' : state === 'נבדק' ? 'graded' : state ? 'submitted' : 'unknown',
    download: file && file.href});
}
[ASSIGN.length, ASSIGN.filter(i => i.due).length, ASSIGN.filter(i => i.download).length].join(' ')
```

Each `ASSIGN` item is a document item: `url` is the assignment's page (its identity: the core matches it on every sync), and the file is downloaded from `download` (not from `url`, which is a page), then `download` is dropped from the item before the listing is saved. Run the size and type snippet on `download`. List every assignment on every sync, also when its file is already downloaded: that is how a status change reaches the core. Last count 0 for `due` or `download` is shown to the student; the assignment is then listed with "no date known" or not at all.

## Terms of use

Every page's footer: materials are uploaded for the personal use of the course's students and for course purposes only; they are the university's property and must not be distributed ("אין להפיץ חומרים אלה"), under the discipline code. So: download for the student's own study only, keep everything in their own course folder, and never publish or share course material. The footer doesn't address recordings separately.

## Not available

- Moodle's `core_courseformat_get_state` AJAX call (older Moodle).
- The Moodle app's web-service token (`login/token.php`): the site's public config says `enablemobilewebservice: 0` (checked 2026-11-21).
