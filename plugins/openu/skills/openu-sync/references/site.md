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
[...d.querySelectorAll('table.generaltable tbody tr')].map(r => {
  const cells = [...r.cells].map(c => c.textContent.trim().replace(/\s+/g, ' '));
  if (cells[0]) section = cells[0];
  const a = r.querySelector('a[href*="/mod/"]');
  return a && {section, name: cells[1], type: new URL(a.href).pathname.split('/')[2], url: a.href};
}).filter(Boolean)
```

Size snippet (same tab; `ITEMS` is the document items built so far, folder files included). It asks for each file's headers only, so nothing downloads:

```js
for (const i of ITEMS) {
  try {
    const r = await fetch(i.url, {method: 'HEAD', credentials: 'include'});
    const n = r.ok && r.headers.get('content-length');
    if (n) i.size = Number(n);
  } catch (e) {}
}
ITEMS
```

Unverified on the live site: whether `/mod/<type>/view.php?...&redirect=1` and `/pluginfile.php/...` answer a `HEAD` request with a `Content-Length`. On the first live sync, check that the returned items carry a plausible `size` (a PDF of a few MB, not a few KB of HTML). If they don't, the item simply has no `size` and the Fetch plan shows "size unknown": nothing else changes. A `url` activity that points to another site has no size either.

## Downloading files

The session cookie is http-only, so scripts can't reuse it. Download from inside the logged-in tab: `fetch(url, {credentials: 'include'})` → `blob` → a temporary `<a download="<name>">` click. Files land in the student's Downloads folder (verified). Chrome may ask once to allow multiple downloads from opal.openu.ac.il: the student approves it.

Put the files in one batch folder by prefixing names, e.g. `unistudent-<course>-<date>__<name>`, and write the listing as a JSON download the same way: `new Blob([JSON.stringify(LISTING)], {type: 'application/json'})` → `URL.createObjectURL` → the same `<a download>` click.

## Recordings

- Video collections: `/mod/ouilvideocollection/view.php?c=<id>`. Each recording is a `.ovc_playlist_title` element (title) inside `.ovc_playlist`; the date and lecturer are next to it.
- Clicking a title loads an iframe `/local/ouil_video/player.php?mediaid=<id>`. In that iframe, `jwplayer_parameters.file` is an HLS playlist on `souvod1.bynetcdn.com` with a time-limited token in the URL. It needs **no cookies**: ffmpeg can download it directly while the token is valid (a few hours). A whole course takes longer than that to download, so a link is collected only after the student's OK, one recording at a time, just before its download.
- Two quality variants: about 1.8 Mbit/s and 0.4 Mbit/s. At 1.8 Mbit/s an hour is about 0.81 GB, so a three-hour session is about 2.4 GB; far less at low quality or audio only, which is all transcription needs. The Fetch plan estimates a recording's size from its length at 1.8 Mbit/s.

Recordings snippet (scan, in the collection tab; collects no links). It returns each title with the text around it, where the date, the lecturer and, when shown, the length are:

```js
[...document.querySelectorAll('.ovc_playlist_title')].map(t => ({
  title: t.textContent.trim(),
  around: t.parentElement.textContent.trim().replace(/\s+/g, ' '),
}))
```

Read the date and the length from `around`. A length (`h:mm:ss` or `mm:ss`) becomes the item's `seconds`; a time of day ("18:00-21:00") is not a length. Unverified on the live site: whether a recording's length is shown next to its title at all, and in which form. On the first live sync, check one collection by eye and record what you find here. No length shown: leave `seconds` out, and the Fetch plan shows the recording as "size unknown".

Stream snippet (download, in the collection tab; only after the student's OK, one recording per run; `ITEM` is that recording's item from the approved listing, `FILE` the one-recording listing's name):

```js
const t = [...document.querySelectorAll('.ovc_playlist_title')].find(e => e.textContent.trim() === ITEM.title);
if (!t) throw new Error('recording no longer on the site');
t.click(); await new Promise(r => setTimeout(r, 4000));
const stream_url = document.querySelector('iframe').contentWindow.jwplayer_parameters.file;
const a = document.createElement('a');
a.href = URL.createObjectURL(new Blob([JSON.stringify({items: [{...ITEM, stream_url}]})], {type: 'application/json'}));
a.download = FILE; a.click();
'saved'
```

The javascript tool hides tokenised URLs from Claude's view, so the snippet writes the link straight into the one-recording listing instead of returning it. `us recordings fetch` downloads from that file.

## Terms of use

Every page's footer: materials are uploaded for the personal use of the course's students and for course purposes only; they are the university's property and must not be distributed ("אין להפיץ חומרים אלה"), under the discipline code. So: download for the student's own study only, keep everything in their own course folder, and never publish or share course material. The footer doesn't address recordings separately.

## Not available

- Moodle's `core_courseformat_get_state` AJAX call (older Moodle). The standard web-service token login wasn't tried: it would need the student's password.
