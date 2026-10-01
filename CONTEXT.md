# UniStudent

A family of Claude plugins that turns a university course's material into a per-course, AI-readable knowledge base and study pages, and keeps Claude's answers grounded in that material.

## Language

### Courses and storage

**Course folder**:
The single self-contained folder holding everything for one course a student takes.
_Avoid_: vault, workspace, project folder

**Settings**:
The per-course, local-only record of the student's choices for that course folder.
_Avoid_: course.yaml, config

**Registry**:
The per-student list of all their course folders.
_Avoid_: course list

### Material

**Raw**:
The untouched mirror of every original file in a course folder.
_Avoid_: downloads, sources folder

**Manifest**:
The record of every file in Raw, with its origin and state.

**Origin**:
Where a file in Raw came from: the course site, the student's own folder, or the inbox.
_Avoid_: source (reserved for citations)

**Inbox**:
The drop zone in a course folder for material the student adds by hand.

**Recording**:
The video file of one course session (מפגש).
_Avoid_: video, lecture

### Knowledge and output

**Wiki**:
The derived, AI-oriented Markdown knowledge base of one course, rebuilt from Raw.
_Avoid_: LLM wiki, knowledge base, index

**Study pack**:
The set of student-facing pages generated for one unit.
_Avoid_: unit summary, unit pack

**Graph**:
A picture in a study pack with X and Y axes and the lines or curves drawn on them, reproducing one the course material shows.
_Avoid_: diagram, plot, chart, figure (a figure is the picture inside the course material itself)

**Unit**:
A chapter of the course as the course itself numbers it (יחידה).

**Topic**:
One of the 4–6 sub-parts of a unit that every page of its study pack is organised by.
_Avoid_: subject, section

### Skill layers

**Course skill**:
A published skill holding the rules for one course's study packs that stay true across semesters.

**Field skill**:
A published skill holding study-pack rules shared by all courses in one academic field.

**Student preferences**:
The study-pack and material-handling rules a student set, in two levels: course preferences and general preferences.
_Avoid_: own rules, local course skill, custom skill

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

**Subject plugin**:
A plugin holding field skills and course skills; it never depends on a university.

### Grounding

**Course material**:
Everything in a course folder's Wiki.

**Official material**:
Course material from the course site, or files the student marks as the lecturer's.

**Added material**:
Course material the student brings from anywhere else.
_Avoid_: unofficial, external

**Grounding label**:
The mark on each paragraph stating where it stands against course material: ✅ from it, 💡 an explanation of it in Claude's own words, ⚠️ outside it, ❌ conflicts with it.
