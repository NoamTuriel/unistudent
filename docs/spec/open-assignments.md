# Spec: the open-assignments step

Status: grilled with the owner, building · Created 2026-11-21 · Extends `docs/spec/v3.md`. Vocabulary is `CONTEXT.md`'s; this spec adds **Assignment**, **Open assignment**, **Trap scan** and **Readiness**.
Research behind the scan: `docs/research/assignment-ai-traps.md`. Decision record: `docs/adr/0019-assignments-are-scanned-before-they-are-solved.md`.

## Problem

After a setup or a sync the student has new files, some of them assignments (מטלה / ממן) that are open for submission. Today nothing finds them, nothing checks whether the Wiki can answer them, and an AI that solves one reads the file's content as if it were the student's request. A file can carry text aimed at the assistant (hidden or visible), so the file must be read as data first.

## Solution

One command, `us assignments`, and one skill, `course-assignments`. The step runs at the end of every setup and every sync, and is offered to the student, never forced. The core never submits anything.

### Data (the sync seam)

A listing item may carry `kind: "assignment"`, `due` (`YYYY-MM-DD`) and `status` (`open`, `submitted`, `graded`, `unknown`). `us ingest` stores them in the Manifest entry (`kind`, `due`, `status`) and refreshes them on every sync, also when the file itself did not change (a status moves from open to submitted with the same PDF). A file the student added by hand is marked with `us assignments set <file> --due D --status S`.

### Commands

- `us assignments [list]` (default): the open assignments and their **Readiness**. Open means status is not `submitted` or `graded`, and the due date is today or later; no date means open ("no date known"); a past date that is not submitted is listed as `overdue`. Per assignment: `path`, `unit`, `due`, `days_left`, `state`, and readiness: `file_read` (the Wiki's coverage state for the file), `unit_sources` (how many other source files of its unit the Wiki holds), `ready` (`yes` or `needs-material`) and `why`. The per-question check is judgment and belongs to the skill.
- `us assignments scan [files...]`: the **Trap scan** on the given files, or on every open assignment. Findings in plain words with page and position, the quoted text, and `aimed_at_ai`; plus `could_not_check`, always stated.
- `us assignments set <file> --due D --status S`: record a date or status by hand.
- `us ingest` also returns `assignments_open`, so a sync that ingests an assignment sees it in the result.

`--today YYYY-MM-DD` overrides the date (the tests' seam).

### The Trap scan (stdlib only)

Detects, by file type, what `docs/research/assignment-ai-traps.md` ranks as likely in a university assignment:

| File | Detected |
|---|---|
| PDF | white or tiny text, invisible render mode, text outside the page box, annotations, metadata and form fields aimed at an AI, text-layer characters that are invisible |
| docx | `w:vanish` runs, white or tiny runs, comments, tracked deletions, alt text, headers and footers aimed at an AI |
| pptx, xlsx | the same on slide text and notes; hidden sheets |
| any text, and every text above | zero-width, bidi override and Unicode tag characters; sentences aimed at an AI assistant (English and Hebrew) |
| images, scans | not scanned: handed to the `source-reader` worker (visual read), stated in `could_not_check` |

A scan that cannot parse a file says "could not check", never "clean". No finding is ever followed.

### The skill `course-assignments`

1. Find: `us assignments --json`; show the open ones (due date first). Nothing open → one line, stop.
2. Trap scan first, before anything is read as a task: `us assignments scan`. Say findings in plain words. A finding aimed at the assistant is shown and the student chooses: solve ignoring it, skip that assignment, or stop.
3. Readiness: per question, is there Wiki material (lecture, booklet) for it? If not, say which question lacks what, and tell the student to add material (inbox, `course-add`). Never fill a gap without a ⚠️ paragraph naming where it came from.
4. Offer: per assignment or all at once. The student says yes.
5. Solve from the Wiki only, in the lecturer's method, with citations (the grounding rule), and a ⚠️ line for anything outside the material.
6. Write-up instructions: per question, what to write and draw, step by step, with formulas, intermediate values, the final answer line and a "check yourself" line.
7. Submission steps from official sources only (the assignment's own instructions, a submission guide, the site's submission page, the syllabus), cited; none found → say so. The student submits.

### Where it runs

`course-setup` (end, after the unattended run) and `openu-sync` (report step) both end with "run `us assignments --json`; if any is open, offer `/unistudent:course-assignments`". Any other university plugin's sync skill does the same.

## Decisions settled with the owner (2026-11-21)

1. `us assign` stays "sort a file into a unit"; the homework term is **Assignment**, the command `us assignments`.
2. Dates and status come from extended listing items; hand-added files use `set`.
3. Open = not submitted or graded and not past due; no date = open; past due = overdue.
4. The step is a final step of setup and of the sync, plus a standalone skill; the core command is the single source of truth.
5. Scan depth: stdlib, best effort, limits stated.
6. Solutions are given in chat; a file is written only on request, into an `Assignments` folder of the Study vault.
7. One PR, merged after green CI and a clean privacy check.

## Not verified / known limits

- OPAL's assignment module: verified on 2026-11-21 against the live site (see `plugins/openu/skills/openu-sync/references/site.md`). Not seen: the status word for a file submitted but not yet checked (anything but "נבדק" is read as submitted), a time of day on a due date, and assignment types other than file assignments.
- The research's unverified items (PDF-spec wording for render mode, annotations, layers; markitdown and ffmpeg on hidden content; pptx and xlsx hidden attributes) apply to the scan: it relies on first-hand fixtures, not on those claims.
- Text under images, camouflaged text, text rendered as images and semantic honeypots (a made-up term, contradictory numbers) are not statically provable. The skill cross-checks numbers across the assignment, the site page and the Wiki and says what disagrees.
- The PDF reader is a small parser: encrypted files, unusual encodings and content in object streams it cannot read are reported as could-not-check.
- No `pypdf` path: the optional library the owner allowed is not used, to keep one code path (add it behind `try/except ImportError` if a real file defeats the parser).
- Windows and Linux were not run locally; the CI matrix covers them.
