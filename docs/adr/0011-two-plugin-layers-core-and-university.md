# Two plugin layers: core and university; per-course rules are the student's preferences file

Supersedes the subject half of ADR 0001 and ticket 02 (generated course rules). The repo ships two plugin layers: the core and one plugin per university. There are no subject plugins, no field or course skills, and no generated per-course rules. A Study pack is built from three rule layers, later wins: the generic rules, General preferences, Course preferences. The per-course layer is the student's Course preferences file (ADR 0002), which the student can read and edit, and nothing else.

We chose this over one field skill per major because the maintainer cannot test rules for a major he has not studied, and the one field that had skills added about ten lines over the tuned generic rules. Those lines now sit in the generic rules as conditional advice ("When the course has …"), applied only when the course has the thing they name. We chose it over an interview because a student cannot say what to emphasise before learning the unit: emphasis comes from the Wiki course page's exam section and the past-exam questions in the question bank.

A course folder whose settings still name a `course_skill` is read as if the key were absent, and a leftover subject plugin installed alongside does nothing; the README says it can be uninstalled.
