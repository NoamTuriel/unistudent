# Study pack: generic rules

The generic rules for building a study pack, used when no field skill, course skill or preference says otherwise. Later layers override earlier ones: generic → field skill → course skill → general preferences → course preferences.

## The student's flow (every format decision serves it)

1. **Roadmap:** see the whole unit and what to memorise versus only understand.
2. **Walkthrough:** learn one whole topic at a time. When something is unclear, ask Claude or jump to the recording.
3. **Practice:** solve that topic's questions.
4. After the unit: the whole practice page in order.
5. Before the exam: the roadmap topic by topic, then past-exam questions by topic to find weak spots.

## Topics: the backbone

Split the unit into 4–6 topics in teaching order (usually the lecture order). Give each a tag `#unit-NN/tNN-short-name` (course language allowed after the number). This one topic list is shared by every page.

## Pages

| Key | Page (Hebrew / English title) | What it gives the student | Default |
|---|---|---|---|
| roadmap | `N.1 מפת דרכים` / `N.1 Roadmap` | Overview, memorise vs understand, per topic: tools, solving order, question types, common mistakes, recording links; checklist | ✓ |
| walkthrough | `N.2 הסבר החומר` / `N.2 Walkthrough` | The big idea, then every concept of every topic, in the concept structure below; per topic: recording segments and its practice questions | ✓ |
| practice | `N.3 תרגול` / `N.3 Practice` | Every question from the course material for this unit, grouped by topic and stage, tagged, with the recording time when it is solved there | ✓ |
| practice-short | `N.3b תרגול מקוצר` / `N.3b Short practice` | Every topic's questions, but only one per distinct way of solving it — for revising fast, not for full practice | |
| recordings | `N.4 תוכן עניינים להקלטות` / `N.4 Recordings index` | Per recording: time · until · type · what happens · topic. Only when the unit's recordings have transcripts | ✓ when transcripts exist |

Save to the unit's folder in the Study vault (`pack_folder` in the result of `us study changes --unit N`): its name, the page titles and the content all follow the course language. The vault holds only study packs and the generated recordings roadmap.

## Accepted reasoning (when the material has verbal solutions)

A verbal solution justifies an answer in words (Q&A files, assignment solutions and past-exam solutions often do). The student's own wording of a justification is often not what the exam accepts; the solved answers show what is. When the unit has any, the roadmap gets an **Accepted reasoning** section, one block per topic that has verbal solutions. Done when every verbal solution of the unit has been read and each block lists:

- **Say it:** the steps a solution spells out, in the solution's own words, quoted (✅, linked to the solution).
- **Take as given:** what solutions use without explaining.
- **Prove it:** what solutions always establish first, which the student must not take as obviously true.
- **Model answer:** one short justification in the solutions' wording, linked.

A pattern seen across several solutions is 💡, stated with the solutions it comes from. A topic with no verbal solution gets no block, and nothing is invented for it.

## Announcements and exam hints (roadmap)

The unit page in the Wiki collects what the lecturer said in this unit's recordings: `Announcements` (dates, assignments, who to work with, exam information) and `This will be on the exam`. The roadmap page always has a section for them, every line with its recording and time link (✅, citing the recording summary). Leave it out only when the unit page lists none. These are first-class: never summarise them away.

## Concept structure (walkthrough)

`### <concept> — <English name>`, then in this order:

1. **In plain words:** one sentence.
2. **Explanation:** why it is so, with a concrete example (usually 💡: your words, resting on the Wiki).
3. **Formula:** on its own line, each symbol explained; "none: a qualitative concept" when there is none.
4. **Memory tip:** one line (💡).

## Practice stages

Stage 0: examples from the slides. Stage 1: questions with answers. Stage 2: the assignment, under exam conditions. Stage 3: past-exam questions for this unit (pure), then questions that combine units (challenge). Each question: topic tag, source link, and the recording time when it is solved there (❌ when an example in the material is never solved in a recording).

## Short practice (practice-short)

For a student short on time: every topic still appears, but with the fewest questions that cover
everything worth practicing — not the fewest questions overall.

- Two questions are **the same** when solving them takes the same method and the same steps, even with
  different numbers or a different scenario. They are **different** when the method or steps differ, even
  if one is much easier than the other. When unsure whether two questions are the same, read both
  solutions before deciding: surface wording never decides it alone.
- Group each topic's questions (across every stage: slide examples, Q&A, assignment, past exams) by that
  test. From each group of "the same" questions, keep only the **hardest** one (the most steps, the most
  combined concepts, or an explicit challenge / combined-unit question) and drop the rest.
- Every group of "different" questions keeps its one question, regardless of difficulty — a question that
  is easy but solved a different way is never redundant.
- Every topic has at least one question here. Keep each kept question's topic tag, source link and
  recording time exactly as on the full Practice page, so it's still checkable and still links back.

## Graphs

Where the course material explains a concept with a graph (X and Y axes with lines or curves), or a question or its solution explicitly needs one, show it on the walkthrough and practice pages (and on a kept short-practice question, the same as on the full practice page). Never on the roadmap, the recordings index or the navigation line, and never a graph that decorates a page the course didn't illustrate. A student preference such as "no graphs" or "only the key ones" overrides this.

1. **Find it:** the Wiki text only hints at a slide's graph (axis labels, words like "curve" or "shifts"), so open that slide page and read it visually, including image-only pages.
2. **Write a Graph spec** into `<pack folder>/graphs/<name>.json`. Keep it short: the axes' labels and every curve with the course's own names. Label each axis with the name in the course language plus the course's symbol in brackets, e.g. `כמות הכסף (M)`, and name a curve by its name plus its symbol when the course gives one. A curve is two points, a vertical or horizontal value, a formula in `x`, or a sketch of a few rough points on a 0–10 grid (for conceptual "what would happen if" graphs; the tool draws it as a smooth curve with no numbers). A shifted curve names the curve it moves from (`shift_of`). Points of interest give two curve names (the tool finds the crossing) or coordinates.
3. **Draw it:** `us graph "<pack folder>/graphs/<name>.json"` (`us`: the UniStudent MCP tool `graph`, or the `unistudent` command). Fix the spec and draw again when it reports a problem. Open the PNG next to the slide page once and fix every difference: the graph must be as close to the course's own as possible (the same curves with the same slopes and shapes, the same labels, the same crossings and points, the same relative positions), because the student will compare the two.
4. **Embed it** with a standard image link, alt text saying in words what the graph shows (which curve shifts, which way, what happens to each variable), and on the next line a caption starting with a grounding label: ✅ and a link to the slide page when it reproduces the course's graph, 💡 when it only illustrates. ⚠️ is not valid for a graph.
5. **Without drawing** (the tool says matplotlib is missing): write no image link; write the slide page link and one line describing the graph, and tell the student once how to add matplotlib.

Flow and cause-and-effect pictures are plain Mermaid blocks, no tool.

## Links

- Citations point at the student's own file in the Material folder, never at the Wiki (the student does not read it): a full disk link, a `file:` URL with the path percent-encoded (`file:///…/<material folder>/official/<unit folder>/slides.pdf`). Write the page or minute in the link text ("slides, page 3", "lecture 3, 00:12:47"). Read the Wiki page's `source:` line to find the file. A file that failed, was skipped or is not analyzed yet (`coverage.md`) is named as such, not cited as read.
- Recordings: link the video file the same way; for a time add `#t=<seconds>` and write the time in the text. The transcript is in the Wiki, so it is not linked.
- `us check` fails a vault page that links into the hidden folder or at a missing file; the Wiki build repairs links after the course folder or a file moves.
- Wikilinks are only for moving between pages of the vault, never for a citation (a citation is the `file:` link above).
- Obsidian format: wikilinks and callouts (`> [!tip]`) are fine. Plain Markdown: standard links and blockquotes only.
- A navigation line at the top of every page linking the unit's other pages.

## Grounding

Label every paragraph as the course context (`.unistudent/context.md`) says.
