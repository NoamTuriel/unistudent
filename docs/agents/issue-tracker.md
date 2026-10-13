# Issue tracker: Local Markdown

Tickets for this repo live as markdown files in `.scratch/`, which is gitignored: ticket history is never pushed (see `CLAUDE.md`, "Privacy").

## Conventions

- The spec for a version is `docs/spec/v<N>.md` (committed); it is the source of truth the tickets point back to.
- Tickets are one file each at `.scratch/unistudent-v<N>/issues/<NN>-<slug>.md`, never a single combined tickets file. Numbering continues across versions: a new ticket takes the next number after the highest in any `.scratch/unistudent-*/issues/`.
- Each ticket opens with a `# <NN>: <title>` heading, then bold header lines:
  - `**What to build:**` the behaviour, in `CONTEXT.md` words
  - `**Blocked by:** NN, NN (why)`, or `None (can start immediately).`
  - `**Status:**` a triage label (see `triage-labels.md`), or `done`, `done (merged into branch v<N>)`, `reverted — …`
  - `**Spec:**` `docs/spec/v<N>.md`, the Solution step and Implementation Decisions it covers
- Then a checklist of `- [ ]` acceptance items.
- A version's work lands on the integration branch `v<N>`; a ticket is resolved by setting its `**Status:**` to `done (merged into branch v<N>)`.
- Comments and conversation history append to the bottom of the file under a `## Comments` heading.

## When a skill says "publish to the issue tracker"

Create a new ticket file under the current version's `.scratch/unistudent-v<N>/issues/` (creating the directory if needed), numbered as above.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the ticket number directly; search `.scratch/unistudent-*/issues/<NN>-*.md` for a bare number.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `**Type:**` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `**Status:**` line records `claimed`/`resolved`.
- **Blocking**: a `**Blocked by:** NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `**Status:** claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `**Status:** resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
