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

Save to `study/Unit N/` (folder names are always English; page titles and content follow the course language).

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
  if one is much easier than the other.
- Group each topic's questions (across every stage: slide examples, Q&A, assignment, past exams) by that
  test. From each group of "the same" questions, keep only the **hardest** one (the most steps, the most
  combined concepts, or an explicit challenge / combined-unit question) and drop the rest.
- Every group of "different" questions keeps its one question, regardless of difficulty — a question that
  is easy but solved a different way is never redundant.
- Every topic has at least one question here. Keep each kept question's topic tag, source link and
  recording time exactly as on the full Practice page, so it's still checkable and still links back.

## Links

- To material: Wiki source pages with page anchors (`wiki/sources/unit-04/slides.md#page-3`).
- To recordings: the transcript anchor (`wiki/recordings/<rec>/transcript.md#001230`) plus the video file link (`file://…`). The video link opens the file; Obsidian's Media Extended plugin can jump to the time.
- Obsidian format: wikilinks and callouts (`> [!tip]`) are fine. Plain Markdown: standard links and blockquotes only.
- A navigation line at the top of every page linking the unit's other pages.

## Grounding

Label every paragraph as the course context (`.unistudent/context.md`) says.
