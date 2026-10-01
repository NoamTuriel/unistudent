# Spec: one plain warning replaces the four grounding labels, and no emoji anywhere else

Status: grilled with Noam, ready to ticket · Created 2026-10-02 · Owner: Noam
Amends the "Grounding rule" in `docs/spec/v1.md` (see ADR 0009, written with this change).

## Problem Statement

Every claim paragraph carries one of four emoji (✅ 💡 ⚠️ ❌) and the student is expected to remember what each means. That is noise to read, hard to remember, renders badly in right-to-left text and in some harnesses, and mostly marks the normal case. What a student needs to know is one thing: when something does **not** come from their course material.

## Solution

1. **Unmarked means from the course.** A paragraph with no warning rests on the course Wiki and ends with a source link, as ✅ paragraphs do today. An explanation, example or memory trick built on Wiki content is also unmarked (the old 💡), and still cites the page it explains.
2. **One warning, in plain words.** A paragraph that uses knowledge not from the Wiki we built (general knowledge, the web, anything else) starts with `⚠️ Not from your course material (general knowledge):` or `(from the web, [link]):`, in the student's language. The words carry the meaning; the student memorises nothing. The wording lives once, in `templates/context.md`.
3. **A conflict is a sentence, not a label.** The old ❌ becomes a ⚠️ paragraph: "The course says X; general practice differs: Y." The course's version comes first.
4. **⚠️ is the only emoji in the repo.** Everything else is plain words: the `us recordings` status marks (`✓ ½ ·`) become "done / partial / none", and icons in READMEs, templates, skills, tests and docs are removed.
5. **No new vocabulary.** `CONTEXT.md` drops "Grounding label" and adds no replacement term.

## Decisions

- Scope of the mark: per paragraph, as labels are today. A paragraph that adds something outside the Wiki gets the mark; the Wiki-based explanation around it stays unmarked.
- `us check` flips: unmarked prose must cite a resolving file link, a ⚠️ paragraph needs no source. Exemptions stay (headings, tables, code, navigation, reports on what the AI did). Study packs keep their own rule (one folded sources block per topic, ticket 20).
- No migration code. Old ✅ / 💡 / ❌ in existing Wiki pages and chats read as plain text and disappear when a page is rebuilt. Breaking rule change, so a minor version bump and a one-line changelog note.
- Docs trail: new ADR 0009 supersedes the four-label decision; update `CONTEXT.md`, `CLAUDE.md` (trust point 1), READMEs, `templates/context.md`, `course-setup`, `reference/study-pack.md`, and the verifier/agents that mention labels; `docs/spec/v1.md` stays as history with a one-line "superseded by ADR 0009" note; rewrite `evals/grounding/cases.json` to expect the warning or its absence.
- Economics and macro skills: strip only the emoji and label mentions now. Their future is the separate TODO (compare with and without them).

## Testing Decisions

Same three seams, through `us.py`. `tests/test_grounding_labels.py` (and the label-aware parts of citations, graphs, folder layout, review fixes, simple study packs) are rewritten: an unmarked paragraph with a resolving link passes; unmarked prose with no link fails; a ⚠️ paragraph with no link passes; leftover ✅ / 💡 text neither passes nor fails by itself. One check that no emoji other than ⚠️ appears in tracked files, so the rule does not drift back.

## Out of Scope

Redesigning the economics/macro skills (next TODO); changing the study-pack shape; migrating existing student folders; translating the warning beyond English and Hebrew.
