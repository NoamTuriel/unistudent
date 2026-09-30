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

## Downloading files

The session cookie is http-only, so scripts can't reuse it. Download from inside the logged-in tab: `fetch(url, {credentials: 'include'})` → `blob` → a temporary `<a download="<name>">` click. Files land in the student's Downloads folder (verified). Chrome may ask once to allow multiple downloads from opal.openu.ac.il: the student approves it.

Put the files in one batch folder by prefixing names, e.g. `unistudent-<course>-<date>__<name>`, and write the listing as a JSON download the same way.

## Recordings

- Video collections: `/mod/ouilvideocollection/view.php?c=<id>`. Each recording is a `.ovc_playlist_title` element (title) inside `.ovc_playlist`; the date and lecturer are next to it.
- Clicking a title loads an iframe `/local/ouil_video/player.php?mediaid=<id>`. In that iframe, `jwplayer_parameters.file` is an HLS playlist on `souvod1.bynetcdn.com` with a time-limited token in the URL. It needs **no cookies**: ffmpeg can download it directly while the token is valid (a few hours), so collect the URLs and download right away.
- Two quality variants: about 1.8 Mbit/s and 0.4 Mbit/s. A three-hour session is about 3 GB at high quality, far less at low quality or audio only, which is all transcription needs.

Stream snippet (in the collection tab):

```js
const out = [];
for (const t of document.querySelectorAll('.ovc_playlist_title')) {
  t.click(); await new Promise(r => setTimeout(r, 4000));
  out.push({name: t.textContent.trim(), stream_url: document.querySelector('iframe').contentWindow.jwplayer_parameters.file});
}
out
```

The javascript tool hides tokenised URLs from Claude's view, so write them straight into the listing download instead of returning them.

## Terms of use

Every page's footer: materials are uploaded for the personal use of the course's students and for course purposes only; they are the university's property and must not be distributed ("אין להפיץ חומרים אלה"), under the discipline code. So: download for the student's own study only, keep everything in their own course folder, and never publish or share course material. The footer doesn't address recordings separately.

## Not available

- Moodle's `core_courseformat_get_state` AJAX call (older Moodle). The standard web-service token login wasn't tried: it would need the student's password.
