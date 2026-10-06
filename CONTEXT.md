# UniStudent

A family of Claude plugins that turns a university course's material into a per-course, AI-readable knowledge base and study pages, and keeps Claude's answers grounded in that material.

## Language

### Courses and storage

**Course folder**:
The single self-contained folder holding everything for one course a student takes. It shows the student two folders at setup (Inbox, Material folder) and a third, the Study vault, once the first Study pack is made, and hides the rest in the Hidden folder.
_Avoid_: vault, workspace, project folder

**Hidden folder**:
The course folder's dot-folder (`.unistudent`) holding everything the student never uses: Settings, Manifest, the Wiki, jobs, saved state.

**Study vault**:
The one visible folder holding only what UniStudent made for the student to study from (study packs, recording roadmaps), opened as an Obsidian vault or in any other app. It is Markdown for a human and never links into the Hidden folder; citations in it are disk links to the student's own files in the Material folder. Its name says what it is for, in the student's language.
_Avoid_: study folder, summaries folder, output folder

**Settings**:
The per-course, local-only record of the student's choices for that course folder.
_Avoid_: course.yaml, config

**Registry**:
The per-student list of all their course folders.
_Avoid_: course list

### Material

**Material folder**:
The visible folder holding the real files of the course, sorted by trust level (official or added) and unit. The student may move, rename or delete files in it; where a file sits is the truth. Not to be confused with *course material*, which is what the AI answers from.
_Avoid_: raw, materials, downloads, sources folder

**Manifest**:
The record of every file in the Material folder, with its origin and state.

**Origin**:
Where a file in the Material folder came from: the course site, the student's own folder, or the inbox.
_Avoid_: source (reserved for citations)

**Inbox**:
The drop zone in a course folder for material the student adds by hand.

**Recording**:
The video file of one course session (מפגש).
_Avoid_: video, lecture

**Recorded lessons**:
The place, outside every unit, for recordings of whole class sessions, which often teach several units at once. It is a folder in both the Material folder and the Study vault, and its recordings are never unsorted.
_Avoid_: lectures folder, general recordings

### Knowledge and output

**Wiki**:
The derived, AI-oriented Markdown knowledge base of one course, rebuilt from the Material folder and kept in the Hidden folder: the student never opens it.
_Avoid_: LLM wiki, knowledge base, index

**Study pack**:
The set of student-facing pages generated for one unit.
_Avoid_: unit summary, unit pack

**Short version**:
The closing list of the Practice page of a Study pack: the must-do questions of the unit, one per distinct way of solving, past-exam questions first. It replaces the separate short practice page.
_Avoid_: short practice, summary list

**Presentation**:
The form (table, steps, flowchart, graph, picture kind) a course uses to teach one topic, as recorded on the unit's Wiki page.
_Avoid_: layout, format

**Graph**:
A picture in a study pack with X and Y axes and the lines or curves drawn on them, reproducing one the course material shows.
_Avoid_: diagram, plot, chart, figure (a figure is the picture inside the course material itself)

**Unit**:
A chapter of the course as the course itself numbers it (יחידה).

**Topic**:
One of the 4–6 sub-parts of a unit that every page of its study pack is organised by.
_Avoid_: subject, section

### Rule layers

**Student preferences**:
The study-pack and material-handling rules a student set, in two levels: course preferences and general preferences.
_Avoid_: own rules, course skill, field skill, custom skill

**Course preferences**:
Student preferences for one course, stored in its course folder; they win over general preferences.

**General preferences**:
Student preferences that apply to all of a student's courses.

### Plugins

**Core**:
The university-agnostic plugin that owns course folders, the Wiki, recordings, study packs and grounding.
_Avoid_: generic skill

**University plugin**:
A plugin holding everything specific to one university: site access, site structure and unit sorting.
_Avoid_: adapter, connector

### Grounding

**Course material**:
Everything in a course folder's Wiki.

**Official material**:
Course material from the course site, or files the student marks as the lecturer's.

**Added material**:
Course material the student brings from anywhere else.
_Avoid_: unofficial, external
