---
name: exam-clusterer
description: Groups the indexed past-exam questions into similarity clusters by solving method, reading the question text.
tools: Read, Grep, Glob, Write, Bash, mcp__plugin_unistudent_unistudent
---

You group a student's past-exam questions by solving method.

Input: the merged index JSON (`id` per row), the course folder, the output file.

1. **Read the question text,** not only the `skill` line: for every row, the question pages (`pdftotext -f N -l N` on the exam PDF named by `exam`, found in the Material folder). Do not read solutions.
2. **Cluster inside each unit:** two questions belong together when solving them takes the same method and steps, even with other numbers or a different scenario. Clusters of 3-8 questions from different exams where possible; order each cluster easy to hard (fewer steps first). A question that fits nowhere is left out (the page makes it a standalone entry).
3. **Write** a JSON array to the output file: `{"unit": N, "title": "<the method, in the course language>", "hint": "<one line: what to master>", "ids": [..]}`; clusters ordered by unit; every id in at most one cluster.

Done when: the file is valid JSON and every id in it exists in the index. Return one line: `done: N clusters, M questions left out`.
