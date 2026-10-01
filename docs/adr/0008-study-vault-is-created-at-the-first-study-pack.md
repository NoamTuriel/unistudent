# The Study vault is created at the first Study pack

Setup creates two visible folders: the Inbox and the Material folder. The Study vault appears when the student first asks for a Study pack. A student who only wants answers from the course never sees an empty third folder, and a missing Study vault is never reported as a problem.

This amends ADR 0007 ("three visible folders"): the layout is still three folders, but the third is created when it is first needed. We chose it over creating all three at setup because an empty folder named "study from here" promises something the student has not asked for, and over a hidden-until-used folder in the Hidden folder because the Study vault must be a normal visible folder the student can open in Obsidian. We accept that the folder count the student sees changes over time, so the setup text and the README say so.
