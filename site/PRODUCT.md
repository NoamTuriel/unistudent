# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS, no build step, served by GitHub Pages from the `site/` folder of the public repo.

## Users

University students at any university, mostly non-technical, preparing for the exams of one specific course. They have a pile of course material (PDFs, slides, past exams, lecture recordings) and already use, or are willing to use, an AI app. Their job: understand the course the way their course teaches it, and pass its exam. Secondary: tech-comfortable students who already use Claude Code, Cursor or Codex.

## Product Purpose

UniStudent is an open-source plugin that turns one course's own material into a per-course Wiki that only the AI reads, so the AI answers from that course and nothing else, and helps the student study it: study packs per unit, recordings with timestamps and the lecturer's announcements, practice from easy questions up to real past exams. Success for the site: a student understands this in seconds, believes it, and installs it.

## Positioning

A general AI answers from the whole internet: other notation, other methods, other courses. The exam grades the course's way. UniStudent keeps the AI inside the student's own course material, links every answer to the exact page or recording minute, and marks anything else with one plain-words warning (⚠️). It lives inside the AI app the student already uses, keeps files in a folder on the student's own computer, and works for any university.

Against NotebookLM (Google, a separate website that answers from uploaded sources): UniStudent is not a separate site; it brings new material in by itself (a university plugin downloads from the course site, or the student drops files in the inbox); recordings get a table of contents with the lecturer's announcements and "this will be on the exam" moments, each linked to the exact minute; per-unit study packs say what to know by heart and what to understand; practice ramps up to real past exams; it is open source (MIT). NotebookLM's strengths (audio overviews, polished general study tools) are real and not to be denied.

## Operating Context

The student installs it once in their AI app (Claude desktop app with Cowork, Claude Code, Cursor, VS Code, Codex, Gemini CLI, any MCP app), then runs course setup per course: it asks one question at a time. New material goes into the course's inbox. Study packs open in Obsidian or any Markdown reader.

## Capabilities and Constraints

- Course folder with an inbox, a Material folder, and a Study vault; the Wiki is hidden.
- Reads and analyzes any course file: PDF, Word, PowerPoint, Excel, scans and photos of notes, recordings (transcribed on the student's own computer).
- Study pack per unit: what to memorize, what to understand, common mistakes, exercise types, plain explanations, the course's illustrations redrawn (graphs, flowcharts, circuits, molecules, family trees).
- Recordings: timestamped table of contents, announcements, "this will be on the exam" moments.
- Before-the-test page: every past-exam question grouped by method, with solution links.
- Ask anything: answers cite the course; outside knowledge carries ⚠️.
- University plugins: `openu` (Open University of Israel) downloads from the course site. Subject plugins: `economics`. Any other university gets a generated, once-interviewed fallback.
- Requires `uv` (one installer). Recordings need ffmpeg.
- Free and open source, MIT.

## Brand Commitments

- Name: UniStudent. Icon: `assets/icon.svg` in the repo (a friendly robot in a graduation cap).
- ⚠️ is the only emoji anywhere in the project.
- Vocabulary from `CONTEXT.md`: course folder, inbox, Material folder, Study vault, Wiki, study pack, unit, recording.
- Voice: plain language, no unexplained jargon, sentence case.
- Nothing personal and no course material ever appears publicly; examples are made up and say so.
- No Israel-specific examples on the site (international audience); prices in euros when needed.

## Evidence on Hand

- 35-second voiced launch video with captions: `site/media/unistudent-35s.mp4`, poster `site/media/unistudent-35s.jpg`, captions `site/media/unistudent-35s.vtt`.
- A made-up grounded answer example (README, economics: why the demand curve slopes down).
- Real repo facts: MIT license, CI on macOS, Windows and Linux.
- Absent, never to be invented: testimonials, user counts, university endorsements, grade improvements, benchmarks, pricing.

## Product Principles

1. Trust first: every claim the site makes about grounding must be literally true.
2. Show the product doing its job rather than describe it.
3. The easiest install path comes first and is written for someone who has never opened a terminal.
4. Any university, any course: never imply it only works for one.
5. Honest comparison: name what competitors do well.

## Accessibility & Inclusion

WCAG AA contrast, keyboard reachable, reduced motion respected, captions on the video, readable on phones (students browse on phones).
