---
name: UniStudent
description: A course reader the student has already marked up; course claims are highlighted and cited in the margin, anything else is flagged.
colors:
  paper: "#fbfbf8"
  ink: "#1d1d1f"
  pencil: "#4f5664"
  rule: "#d6d6cf"
  highlighter-yellow: "#fff15a"
  highlighter-green: "#a6f06a"
  highlighter-green-deep: "#8ddf4c"
  highlighter-pink: "#ff9ccb"
  code-wash: "#f0f0ea"
  sheet: "#ffffff"
typography:
  display:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(2.6rem, 5vw, 4.5rem)"
    fontWeight: 760
    lineHeight: 1
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(2rem, 3.6vw, 3rem)"
    fontWeight: 720
    lineHeight: 1.08
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "1.45rem"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.02em"
  lede:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(1.2rem, 1.7vw, 1.4rem)"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.62
  hand:
    fontFamily: "Kalam, Bradley Hand, cursive"
    fontSize: "1.18rem"
    fontWeight: 400
    lineHeight: 1.3
  folio:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "0.95rem"
    fontWeight: 400
  label:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "1.12rem"
    fontWeight: 700
    lineHeight: 1
  code:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "0.86em"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  focus: "2px"
  sheet: "3px"
  figure: "4px"
  code: "5px"
  button: "6px"
  disc: "50%"
spacing:
  measure: "52rem"
  margin: "15rem"
  gap: "clamp(1.5rem, 3vw, 3.5rem)"
  edge: "clamp(1rem, 4vw, 3rem)"
  section: "clamp(4rem, 9vw, 7.5rem)"
components:
  button-primary:
    backgroundColor: "{colors.highlighter-green}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.button}"
    padding: "0.95rem 1.4rem"
  button-primary-hover:
    backgroundColor: "{colors.highlighter-green-deep}"
    textColor: "{colors.ink}"
  button-copy:
    backgroundColor: "{colors.highlighter-green}"
    textColor: "{colors.ink}"
    rounded: "{rounded.figure}"
    padding: "0.45rem 0.8rem"
  button-copy-hover:
    backgroundColor: "{colors.highlighter-green-deep}"
  margin-note:
    textColor: "{colors.pencil}"
    typography: "{typography.hand}"
    padding: "0 0 0 0.9rem"
  source-page:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sheet}"
    padding: "1rem 1.05rem 1.1rem"
  command-block:
    backgroundColor: "{colors.code-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.code}"
    padding: "0.95rem 6.2rem 0.95rem 1rem"
  step-number:
    backgroundColor: "{colors.highlighter-green}"
    textColor: "{colors.ink}"
    rounded: "{rounded.disc}"
    size: "2.9rem"
  tab:
    textColor: "{colors.pencil}"
    padding: "0.5rem 0 0.55rem"
  tab-selected:
    textColor: "{colors.ink}"
---

# Design System: UniStudent

## Overview

**Creative North Star: "The Annotated Course Reader"**

The page is a printed course reader that a diligent student has already worked through. Everything set in type is the printed book: a serif text column on coated white paper, running heads, page numbers, numbered figures and ruled tables. Everything the student added is in pencil and highlighter: handwritten notes in a right-hand margin, and three highlighters whose colors carry fixed meanings. The visitor reads the product's promise the way they would read their own marked-up course.

Density is a reading density, not a dashboard density: one measure-limited text column with a narrower margin beside it, generous section breaks, no grid of tiles. Depth is paper on paper. Motion is a highlighter stroke drawn once and a cited page unfolding when opened; nothing loops or decorates. The world refuses the AI-tool landing default: no dark hero, no gradient wash, no feature-card grid, no hero code block.

**Key Characteristics:**
- A two-column reader: text column plus handwritten margin, collapsing to one column with notes falling in under what they annotate.
- Three highlighters with fixed meanings: yellow is from your course, green is do this, pink is not from your course.
- Literata for all print, Kalam only for the student's hand.
- Running head with page numbers as navigation; folios ("p. 2") in the margin.
- Boxes exist only as the reader's own objects: figures, ruled tables, a pulled-out source page, a command to copy.

## Colors

A near-white paper and near-black ink carry everything; color comes only from highlighters, and each highlighter means one thing.

### Primary
- **Course Yellow** (highlighter-yellow): the "from your course" highlighter. Marks grounded claims in the example answer, the matching sentence on the cited source page, lecturer announcements in a recording's table of contents, the headline's second sentence, the key's "No mark" entry, and text selection. Also the dot fill on redrawn graphs.

### Secondary
- **Action Green** (highlighter-green): the "do this" highlighter. Fills the Install button, the copy buttons, the numbered install-step discs, and highlights the exact phrases the student should say to their AI.
- **Pressed Green** (highlighter-green-deep): hover state of every green-filled control.

### Tertiary
- **Warning Pink** (highlighter-pink): the "not from your course" highlighter. Used only on the ⚠️ paragraph and the key's "⚠️ Warning" entry.

### Neutral
- **Reader Paper** (paper): page background and scrollbar track.
- **Print Ink** (ink): all printed text, focus rings, graph strokes, the heavy top and bottom rules of tables, the selected tab underline.
- **Pencil Grey** (pencil): handwritten margin notes, their left stroke, folios, captions, fine print, link underlines at rest, list markers, unselected tabs.
- **Hairline Rule** (rule): running-head and footer rules, table row dividers, table-of-contents rows, the key's top rule, tab baseline.
- **Code Wash** (code-wash): background of commands the student copies, block and inline.
- **Loose Sheet** (sheet): the pure-white cited source page, a sheet lifted off the reader paper.

### Named Rules
**The Three Highlighters Rule.** Yellow means from your course, green means do this, pink means not from your course. A highlighter is never used for emphasis or decoration outside its meaning, and no fourth accent is introduced.

**The Ink Carries Text Rule.** Highlighters are backgrounds behind ink, never text colors. Text on any highlighter is ink.

## Typography

**Display Font:** Literata (with Iowan Old Style, Georgia, serif)
**Body Font:** Literata (with Iowan Old Style, Georgia, serif)
**Hand Font:** Kalam (with Bradley Hand, cursive)
**Mono:** ui-monospace, SF Mono, Menlo, Consolas (commands only, at 0.86em)

**Character:** One optical-size serif sets everything printed, from a heavy, tightly tracked headline to the body text, so the page reads as one book. Kalam is the only other voice: the student's pencil in the margin.

### Hierarchy
- **Display** (760, clamp 2.6 to 4.5rem, line-height 1.0, -0.03em): the hero headline only; the closing headline reuses the same weight and tracking at clamp 2.3 to 4.2rem, max 16ch.
- **Headline** (720, clamp 2 to 3rem, 1.08): section titles, one per reader "page".
- **Title** (700, 1.45rem; 1.5rem for install steps): subsections inside a page.
- **Lede** (400, clamp 1.2 to 1.4rem, 1.5, max 40ch): the one-sentence subhead under the headline.
- **Body** (400, 1.125rem, 1.62, max 68ch): running text; drops to 1.06rem under 40rem.
- **Hand** (Kalam 400, 1.18rem, 1.3; bold 700 in ink for emphasis and for citations): margin notes and the citation summary.
- **Folio** (Literata italic 400, 0.95rem, pencil): page numbers in the margin and the running head's "p. N".
- **Label** (700, 1.12rem, line-height 1): the Install button; copy buttons and tabs use 600 to 700 at 0.88 to 1rem.

Headings use `text-wrap: balance`; time stamps use tabular numerals.

### Named Rules
**The Print and Pencil Rule.** Literata is what the course printed; Kalam is what the student wrote. Kalam never sets a heading, a button or body text, and Literata never sets a margin note.

## Layout

A centered page whose width is the text measure (52rem) plus the margin (15rem), the column gap (clamp 1.5 to 3.5rem), and an edge gutter on both sides (clamp 1 to 3rem). Every block is a row: main content in the first column, an optional margin note in the second, aligned to the top of what it annotates. Sections open with clamp 4 to 7.5rem of space above; the hero opens with clamp 2.5 to 4.5rem.

Breakpoints:
- **Above 62rem:** two columns. An opened citation's source page floats over the margin so the answer text does not move.
- **At 62rem and below:** one column. Margin notes fall in under what they annotate (max 34rem); folios and the running head's page numbers are hidden; a note that holds only a folio disappears.
- **At 40rem and below:** body to 1.06rem; the running head wraps and drops secondary links; the two-column study-pack excerpt stacks; the comparison table becomes one labeled block per row; step discs shrink to 2.4rem; copy buttons move to the bottom of their command block.

## Elevation & Depth

Flat paper with a few objects lying on it. The page itself has no shadows; depth appears only on things that are physically separate from the reader: the video figure, a cited source page lifted out of the course, and the Install button. Each uses a soft two-part shadow in ink at low alpha, a tight contact shadow plus a long, negatively spread drop.

### Shadow Vocabulary
- **Figure on page** (`box-shadow: 0 2px 4px rgb(29 29 31 / .08), 0 18px 40px -22px rgb(29 29 31 / .5)`): the video, Figure 1.
- **Loose sheet** (`box-shadow: 0 1px 2px rgb(29 29 31 / .12), 0 14px 28px -16px rgb(29 29 31 / .45)`): the cited source page.
- **Pressable** (`box-shadow: 0 1px 0 rgb(29 29 31 / .25), 0 6px 14px -8px rgb(29 29 31 / .45)`): the Install button.

### Named Rules
**The Objects Only Rule.** Only a physical object on the page casts a shadow: a figure, a lifted sheet, a pressable button. Text blocks, notes, tables and sections stay flat.

## Shapes

Print is square; the few rounded corners are small and belong to objects. Corners step from a 2px focus ring, to a 3px source sheet, 4px video and copy buttons, 5px command blocks, 6px Install button. The install-step numbers are full circles, the only round shape. Structure is drawn with rules, as a book does: hairlines between rows, a 2px ink rule above and below the comparison table, a 1px pencil stroke down the left of every margin note. Highlighter marks are slanted strokes, not boxes: a 101-degree gradient with soft ends, 80% of the line height, cloned across line breaks.

## Components

### Buttons
Highlighter-green and tactile, there to be pressed.
- **Shape:** gently rounded (button token).
- **Primary (Install):** green fill, ink label at label typography, the Pressable shadow.
- **Hover / Active:** fill moves to Pressed Green and lifts 1px; returns on press. Transitions 0.15s ease-out.
- **Copy:** smaller green button pinned to the top right of its command block (bottom right on phones); hover to Pressed Green.
- **Quiet link:** the secondary action beside Install is a plain link at weight 600, never a second button.
- **Sound toggle:** a button styled as an underlined link in the caption.

### Links
Ink text with a 1px pencil underline offset 0.18em; on hover the underline turns ink and thickens to 2px. Focus is a 2px ink outline, 3px offset.

### Margin note (signature)
Kalam in pencil, a 1px pencil rule down its left edge, 0.9rem inset. Bold words switch to ink. A folio may head the note. Notes annotate; they never hold primary content that is missing from the text column.

### Citation and source page (signature)
A margin citation ("Unit 2, p. 14") is a disclosure in bold Kalam with an underline and a pencil "(open it)" hint. Opened, it unfolds a white source sheet: a running head (unit left, page right, italic pencil, hairline below), a bold section title, the cited sentence highlighted yellow, and a "made-up" note. Unfold is 0.35s, translate 6px and scale from 0.98, only when motion is allowed.

### Highlights
Yellow, green and pink marks behind ink text, per the Three Highlighters Rule. The hero's yellow mark draws itself once on load (background-size 0 to 100% over 1.1s, cubic-bezier(.16, 1, .3, 1), 0.35s delay) and is simply present under reduced motion.

### Figures
Numbered, captioned in pencil with "Figure N." in bold ink. Redrawn graphs are inline SVG in ink strokes with pencil dashed guides and yellow-ringed points, labels in Literata.

### Tables and lists
- **Comparison table:** book-style rules only, no fills; 2px ink above and below, 1px ink under the header, hairlines between rows; caption below in pencil. On phones each row becomes a block with inline column labels.
- **Recording contents:** a ruled list with a tabular time column (5.2rem) and the entry; announcements highlighted yellow with a bold tag.
- **Install steps:** numbered by green discs set in display weight.

### Tabs
Text tabs on a hairline baseline: pencil at rest, ink on hover, ink with a 3px ink underline when selected.

### Navigation
The running head: brand (icon plus bold wordmark) left, contents links right, each followed by an italic pencil page number. Hairline rule below. Page numbers hide at 62rem; secondary links hide at 40rem.

## Do's and Don'ts

### Do:
- **Do** set every printed word in Literata and every handwritten word in Kalam, per the Print and Pencil Rule.
- **Do** mark meaning with the three highlighters only: yellow for from your course, green for actions, pink for the ⚠️ note.
- **Do** put asides, reassurances and citations in the margin as pencil notes, and let them fall under their text on narrow screens.
- **Do** number figures and steps, and give each section a page number in the running head and margin.
- **Do** draw structure with rules (hairline, 2px ink for table bounds) rather than fills.
- **Do** gate every animation behind `prefers-reduced-motion: no-preference`.

### Don't:
- **Don't** use a dark hero, gradient backgrounds, or a feature-card grid.
- **Don't** box content that is not a reader object; the only boxes are figures, tables, a lifted source page and copyable commands.
- **Don't** use a highlighter for decoration or generic emphasis, and don't add a fourth accent color.
- **Don't** set text in a highlighter color or put anything but ink on a highlighter.
- **Don't** add shadows to text, notes, tables or sections, per the Objects Only Rule.
- **Don't** use any emoji other than ⚠️.
