# Study pack: generic rules

The generic rules for building a study pack, used when no preference says otherwise. Later layers override earlier ones: generic → General preferences → Course preferences.

## The student's flow (every format decision serves it)

1. **Roadmap:** see the whole unit and what to memorise versus only understand.
2. **Walkthrough:** learn one whole topic at a time. When something is unclear, ask Claude or jump to the recording.
3. **Practice:** solve that topic's questions.
4. After the unit: the whole Practice page in order.
5. Before the exam (or the course's end, when it has no exam): the roadmap topic by topic, then the Short version to find weak spots.

## Topics: the backbone

Split the unit into 4–6 topics in teaching order (usually the lecture order). This one topic list is shared by every page. Topics carry no tags.

## Pages

| Key | Page (Hebrew / English title) | What it gives the student | Default |
|---|---|---|---|
| roadmap | `N.1 מפת דרכים` / `N.1 Roadmap` | How to start, the idea, what to know by heart, a table of topics, the solving order, a checklist, all sources (folded) | yes |
| walkthrough | `N.2 הסבר החומר` / `N.2 Walkthrough` | The big idea, then every topic with its concepts (below), its "How to answer" block, and its folded sources | yes |
| practice | `N.3 תרגול` / `N.3 Practice` | A table of topics with question counts; per topic its questions linked, easy to hard; the Short version at the end | yes |
| recordings | `N.4 תוכן עניינים להקלטות` / `N.4 Recordings index` | One line per recorded lesson that covers the unit, pointing into the Recorded lessons roadmap, then that lesson's announcements and exam hints (below) | yes, when such a lesson exists |

Save to the unit's folder in the Study vault (`pack_folder` in the result of `us study changes --unit N`): its name, the page titles and the content all follow the course language. The vault holds only study packs and the generated recordings roadmap.

Every part earns its place: a page says only what a student reads, and a part with nothing to say is not written (no "none", no filler, no decoration).

Everything on a page, every heading and every label such as "Sources", is in the course language. Never mix in English words for structure.

## Reading in a right-to-left language

A formula, an arrow chain or any run of Latin letters or symbols (`r↑`, `Y↑ → C↑`, `G↑`) goes on its own line, never inside a Hebrew sentence: mixed in a sentence the order of the pieces jumps around. A sentence may name a single symbol; the chain it belongs to sits on the line below.

## Sources (walkthrough)

The text of a topic has no links and no source names: nothing breaks the reading. At the end of each topic, one **folded** block holds the sources, closed by default (a good summary means the student rarely opens it). In Obsidian format it is a foldable callout (`> [!note]- <Sources, in the course language>`); in plain Markdown a `<details>` block. Inside it two lines:

- **In the recordings:** each recording linked once, then the times it is taught or solved as plain text after the link (Links, below). A topic no recording covered has no such line. A recording without a transcript is shown by its file name alone, with no time.
- **From:** the source files the topic rests on. Link text is the file's plain name ("the slides of lectures 8–9"), never a page or slide number. A file with no link is named by its file name.

Chat answers keep a link on every claim.

## How to answer (inside each topic of the walkthrough)

A verbal answered question is a question whose solution justifies the answer in words; Q&A files, assignment solutions and past-exam solutions often have them. The student's own wording of a justification is often not what the course accepts; the solved answers show what is. A topic that has verbal answered questions gets a short **How to answer** block (its name, and the labels **Model answer**, **Say it**, **Prove it** below, are in the course language), after its concepts. Done when every verbal answered question of the topic has been read and the block gives:

- **Model answer:** one short justification as a chain, in the solutions' own wording.
- **Say it:** the steps a solution spells out, quoted.
- **Prove it:** what solutions always establish first, which the student must not take as obviously true.

A pattern seen across several solutions is stated with the solutions it comes from. A topic with no verbal answered question gets no block, and nothing is invented for it. The roadmap only points to each topic's block.

A quote in a Model answer or Say it is copied word for word from the solution: `us check` fails a quote the unit's source pages do not contain (`quote`). It finds the two labels written in English or, in Hebrew, as **תשובה לדוגמה** and **ככה אומרים**.

## Roadmap page

The page the student reads first, in this order, each part only when it has something to say:

1. **How to start:** three numbered steps, each linked to the page it names, so the student knows how to use the pack: brief this page (where the unit is going, what to know by heart, which tools to master), then read the full explanation (the Walkthrough), then test yourself on the Practice page. End with this fixed sentence, written in the course language, its example request built from one of this unit's own concepts: "UniStudent draws graphs and flowcharts on request: ask in chat, for example \"draw the graph of <concept>\"."
2. **The idea** of the unit, one or two lines.
3. **What to know by heart and what to understand:** one list for the whole unit, not one per topic.
4. **A table of the unit's topics**, the same names and order as the walkthrough: per topic its tool, the question that recurs, the common mistake, and a pointer to the topic's "How to answer" block (only when it has one).
5. **The solving order**, a few short steps.
6. **What the lecturer said** (the section below).
7. **A checklist** before the exam (or the course's end, when it has no exam).
8. **All the unit's sources:** one folded block (closed by default, a foldable callout in Obsidian format, `<details>` in plain Markdown) listing every source file and recording of the unit as links, plain names only. The roadmap is where a student looks for where things are, so this is the one place the whole unit's sources are together.

What to know by heart and each topic's recurring question come from the Wiki course page's Exam format section and from the past-exam questions in the question bank, never from the student.

Formulas and Latin symbols follow the right-to-left rule above.

## Concepts (walkthrough)

`### <concept> — <English name>` (only concepts use `###`; the big idea and the closing sections do not). A concept is presented in the form its source uses: a ledger or a two-column comparison is a table, a procedure is numbered steps, a cause chain of three or more steps is a flowchart, a curve is a Graph (both below); prose only where the source is prose. The topic's Presentation line on the unit's Wiki page names the form and the page that shows it. Whatever the form, the concept passes this coverage checklist, each item only when the concept has it:

- **What it is:** one sentence in plain words.
- **Why it is so:** with a concrete example, in your own words, resting on the Wiki.
- **Formula:** on its own line, each symbol explained.
- **Memory tip:** one line, only when a real one exists.

## Practice page

1. A table of the unit's topics with how many questions each has.
2. Under each topic, every suited question from the course material, easy to hard, as one checklist bullet (`- [ ]`, so the student ticks what is solved): the question's number and source page (`שאלה 3, עמוד 4`, in the course language), a link to the question, a link to its solution right beside it, and one line saying what it exercises. Nothing else per question: no stage, no tag, no recording time.
   - **Links:** full `file:` links to the student's own file with `#page=N`. The solution link is the solution's page (same file or the solutions file); a question with no solution in the files says so in words instead of a link. A question with no page anchor (a `.doc`, a scan) links the file by its plain name and says in words where in it to look. Check the layout before linking: render the page and look, never assume the solution is on the next page.
   - **Hide the answer:** when the question's page also shows the solution (handwritten answer on the same page, or the solution on the page right after in the same PDF), make a single-page copy of the question page (`pdfseparate -f N -l N`) in the unit's folder in the Study vault and link the question to it. Never modify the original. A page whose answer can't be hidden says so in the link text.
   - **Groups:** inside a topic, put similar questions together, 3-8 from different sources, easy to hard, so a student who fails one and understands its solution meets the same idea next. Each group opens with one line on what to master. Questions that fit no group stand alone.
3. Ends with the **Short version**, introduced by one line saying what it is: the must-do questions, one per distinct way of solving, past-exam questions first.

No graphs on the Practice page.

### Short version

For a student short on time: every topic still appears, but with the fewest questions that cover everything worth practicing.

- Two questions are **the same** when solving them takes the same method and the same steps, even with different numbers or a different scenario. They are **different** when the method or steps differ, even if one is much easier than the other. Decide it after you read both solutions: surface wording never decides it alone.
- Group each topic's questions by that test. From each group of "the same" questions keep only the **hardest** one (the most steps, the most combined concepts, or an explicit challenge or combined-unit question).
- Every group of "different" questions keeps its one question, regardless of difficulty.
- Every topic has at least one question. Past-exam questions come first.

## Recordings index page

Only **recorded lessons**: recordings of a whole class session, which belong to no unit (the Recorded lessons folder of the Study vault). The first line of each lesson's summary says which units it covers; use it to decide which lessons cover this unit. A recording that solves one question is never pointed to here; the other pages still cite it. A unit no recorded lesson covers gets no Recordings page at all, not an empty one.

One line per covering lesson, in lesson order: the lesson (its summary line), where in it the unit's part starts (linked at that time), and roughly how long that part is, with a link to the lesson's entry in the Recorded lessons roadmap. Under each lesson's line, the lesson's `Announcements` and `This will be on the exam` sections from its summary, in full: every line with its time, in their own two headings. Leave a heading out only when the summary has none. These are first-class: never summarise them away, a student must never miss what the lecturer said out loud. Nothing else: the full timeline lives only in the roadmap.

## Graphs

Where the course material explains a concept with a graph (X and Y axes with lines or curves), or a question or its solution explicitly needs one, show it in that topic on the walkthrough page. Never on the roadmap, the Practice page, the recordings index or the navigation line, and never a graph that decorates a page the course didn't illustrate. A student preference such as "no graphs" or "only the key ones" overrides this.

1. **Find it:** the Wiki text only hints at a slide's graph (axis labels, words like "curve" or "shifts"), so open that slide page and read it visually, including image-only pages.
2. **Write a Graph spec** into `<pack folder>/graphs/<name>.json`. Keep it short: the axes' labels and every curve with the course's own names. Label each axis with the name in the course language plus the course's symbol in brackets, e.g. `כמות הכסף (M)`, and name a curve by its name plus its symbol when the course gives one. A curve is two points, a vertical or horizontal value, a formula in `x`, or a sketch of a few rough points on a 0–10 grid (for conceptual "what would happen if" graphs; the tool draws it as a smooth curve with no numbers). A shifted curve names the curve it moves from (`shift_of`). Points of interest give two curve names (the tool finds the crossing) or coordinates.
3. **Draw it:** `us graph "<pack folder>/graphs/<name>.json"` (call the UniStudent MCP tool `graph` first; use the `unistudent` command only when no such tool is available). Fix the spec and draw again when it reports a problem. Open the PNG next to the slide page once and fix every difference: the graph must be as close to the course's own as possible (the same curves with the same slopes and shapes, the same labels, the same crossings and points, the same relative positions), because the student will compare the two.
4. **Embed it** with a standard image link, alt text saying in words what the graph shows (which curve shifts, which way, what happens to each variable), and on the next line a one-line caption, with a link to the slide page when it reproduces the course's graph.
5. **Without drawing** (the MCP `graph` tool itself says it could not draw): write no image link; write the slide page link and one line describing the graph in words. The student is never told to install anything. A spec mistake is not this case: fix the spec and draw again.

A cause-and-effect chain of three or more steps (`G↑ → AD↑ → Y↑ → …`) is drawn as a Mermaid flowchart in the topic that explains it (a plain Mermaid block, no tool; `flowchart RL` in a right-to-left language, short Hebrew labels), instead of an arrow line. Horizontal over vertical: a chain longer than about five steps is split into several short horizontal flowcharts, each its own `flowchart RL` of up to five steps, never one cramped row and never a tall column. Write each step's direction as a word (עולה / יורד) next to the symbol, not as an arrow glued to it, so a right-to-left box cannot flip it. One or two steps stay a formula line. Other flow pictures are Mermaid too; never a graph drawn with the tool for a flow.

A picture the course shows that is not a graph or a flow is a slide link plus one line in words.

## When the course has …

Each item applies only when the course material has it.

- **models that shift:** draw a shift as the original curve, the moved curve (`shift_of`) and both equilibria, labelled as the course labels them. Give each change the material covers as a chain: which curve moves, which way, what happens to each variable.
- **an assumptions sheet:** quote the assumptions a model relies on by number.
- **a formula sheet:** everything not on it is "know by heart" on the roadmap; check it line by line for what applies to the unit.
- **verbal solutions:** the Model answer is a chain in the solutions' own words (which curve or variable moves, which way, what happens to each variable, ending in the answer). Say it quotes how the solutions name each curve and each direction of change, and the assumption they state aloud. Prove it lists the steps a solution gives that look obvious (an assumption holding, why a curve shifts, why a variable stays fixed).
- **explanations of wrong answers** (Q&A files, assignment solutions): the roadmap's common mistakes come from them.
- **two units using one name for two concepts:** a cross-reference warning at the end of the concept, in both units.

## Links

- In a Study pack, citations are the folded sources block of each topic, not a link on every paragraph. A citation points at the student's own file in the Material folder, never at the Wiki (the student does not read it): a full disk link, a `file:` URL with the path percent-encoded (`file:///…/<material folder>/official/<unit folder>/slides.pdf`). Link text is the file's plain name; a recording's time goes in the text ("lecture 3, 00:12:47"), never a page or slide number. Read the Wiki page's `source:` line to find the file. A file that failed, was skipped or is not analyzed yet (`coverage.md`) is named as such, not cited as read.
- Recordings: one `file:` link per recording per section (heading to heading), to the video file the same way, with `#t=<seconds>` of its first time; every time follows it as plain text (`[lecture 3](file:///…/lecture%203.mp4#t=767) 00:12:47, 00:30:10`). `us check` fails a recording linked twice in one section and a time with no recording link before it in its section. The transcript is in the Wiki, so it is not linked.
- `us check` fails a vault page that links into the hidden folder or at a missing file; the Wiki build repairs links after the course folder or a file moves.
- Wikilinks are only for moving between pages of the vault, never for a citation (a citation is the `file:` link above).
- Obsidian format: wikilinks and callouts (`> [!tip]`) are fine. Plain Markdown: standard links and blockquotes only.
- A navigation line at the top of every page linking the unit's other pages.

## Grounding

A Study pack carries no per-paragraph sources or warnings: the Wiki is the student's knowledge base and the packs rest on it. Say only what the Wiki supports and bring in nothing from outside; if the student wants a line's source, they ask in chat, where answers follow the grounding rule in the course context (`.unistudent/context.md`).

Every Latin symbol and assumption number a page uses is listed in the unit page's Notation or Assumptions sections: `us check` fails one that is not (`notation`; in an English course it reads symbols inside `$…$` math only). The check is reliable for formulas and Latin symbols and weak for course-language terms: those are checked only against the glossary, by the verifier.
