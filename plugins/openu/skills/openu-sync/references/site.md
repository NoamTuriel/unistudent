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

- Video collections: `/mod/ouilvideocollection/view.php?c=<id>`. Each recording is a `.ovc_playlist_title` element (title) inside `.ovc_playlist`; the date and lecturer are next to it.
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
  window.RECS.push({title: T[n].textContent.trim(), around: T[n].parentElement.textContent.trim().replace(/\s+/g, ' '),
                    seconds: seconds || undefined});
}
window.RECS.length + ' of ' + T.length
```

Run it again until it says all of them, then read `window.RECS` (titles, `around`, `seconds`; no links in it). Read the date from `around`; `seconds` 0 or missing means the player didn't load: leave it out, and the Fetch plan shows that recording as "size unknown".

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

## Terms of use

Every page's footer: materials are uploaded for the personal use of the course's students and for course purposes only; they are the university's property and must not be distributed ("אין להפיץ חומרים אלה"), under the discipline code. So: download for the student's own study only, keep everything in their own course folder, and never publish or share course material. The footer doesn't address recordings separately.

## Not available

- Moodle's `core_courseformat_get_state` AJAX call (older Moodle). The standard web-service token login wasn't tried: it would need the student's password.
