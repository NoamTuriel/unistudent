# Assignments are scanned before they are solved, and the student decides

An assignment file is data the student was handed, and some carry text aimed at an AI assistant: hidden (white or tiny text, invisible characters, comments) or visible ("if you are an AI, do X"). An assistant that reads such a file as a task may obey it. So the open-assignments step runs a Trap scan on every assignment before anything is solved, tells the student in plain words what it found and where, and never follows anything found there. A finding is shown and the student decides; the scan never blocks by itself and never acts by itself.

We chose a stdlib scan with stated limits over a bigger parser or a model-only check: the scan is cheap, runs the same on every OS and in every client, and its output (page, position, quoted text) is checkable by the student. What it cannot see (text under images, camouflage, made-up terms and contradictory numbers) is named in every report as `could_not_check`, and "could not parse" is never reported as "clean". Images go to the visual-read worker.

The step also never submits and never fills a gap from general knowledge without the ⚠️ warning (ADR 0009). Solutions are given in chat; a file is written to the Study vault only on request. Dates and status come from extended listing items (`kind: "assignment"`, `due`, `status`) that `us ingest` keeps current in the Manifest; this makes the listing the contract between a university plugin and the core, so the unverified part (reading them from the live site) stays inside the university plugin.

The command is `us assignments`, not `us assign`, which already means "sort a file into a unit".

Shipped in unistudent 0.9.0 and openu 0.5.2.
