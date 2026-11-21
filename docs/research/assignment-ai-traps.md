# AI-targeted traps in university assignment files

Purpose: describe what such traps look like inside a file, so a defensive detector
can warn the student and protect their AI assistant from obeying hidden instructions.
No generation or exploit tooling here; only "what the file contains" and how to spot it.

Researched 2026-11-21. Every claim carries a source. `[unverified]` = I could not confirm it
from a page I fetched or saw in search results (see "Could not verify").

Detector legend used in every table:
- **(a) stdlib** = Python standard library only (zipfile + xml.etree, re + zlib for PDF streams, unicodedata).
- **(b) ffmpeg / markitdown** = what those tools surface.
- **(c) visual-read** = subagent that sees rendered page images and compares them with the text layer.

## 1. Background: what is practiced and studied

### 1.1 Instructions aimed at the assistant ("if you are an AI, do X")
- OWASP defines indirect prompt injection as an LLM accepting input from external
  sources "such as websites or files", and says the content need not be
  human-visible/readable "as long as the content is parsed by the model".
  https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- Observed purposes of hidden prompts in real documents (PhantomLint, 113 real positive
  documents): manipulating peer review, pushing hiring recommendations in CVs,
  summarisation sabotage, tracking LLM use (a prompt asked for a GET request to a URL),
  destructive commands such as "delete all data". https://arxiv.org/html/2508.17884v2

### 1.2 Educator-side "Trojan horse" / canary practice
- Reported case: a history professor (Alcorn State) made an instruction white-on-white
  in a midterm, telling any AI assistant to include the word "Madagascar" in an
  unrelated place; students who pasted the exam into a chatbot passed it along. He
  revealed it after grading. Font size not stated.
  https://www.ibtimes.co.uk/professors-ingenious-trap-exposes-ai-cheating-1811438
- Further detail (small white font, odd canary requests, ethics criticism, counts such as
  "32 of 35") comes from search snippets only; the Chronicle and TechSpot pages returned
  HTTP 403 when fetched, so treat as secondary:
  https://www.chronicle.com/article/is-it-ok-to-lie-to-catch-cheaters
  https://www.techspot.com/news/113243-professor-invisible-prompt-trap-catches-32-students-cheating-with-ai.html
- Implication: the educator's trap targets the student's AI, so the student is the one to
  warn. These traps are typically plain text hidden only by styling (colour/size): the
  cheapest class to detect.

### 1.3 Academic work on hidden prompts in documents
- PhantomLint: detection of hidden LLM prompts in PDF/HTML; all 26 synthetic docs
  detected; 3 false positives in 3,257 ICML papers (OCR failures from non-English
  characters or very small fonts). https://arxiv.org/html/2508.17884v2
- Split-View PDFs: 25 "extraction gaps" in four families (semantic overrides, hidden
  semantic injection, reading-order splits, font-decoding splits), 16 PDF stacks, 7
  commercial LLM services; every service exposed at least one gap; authors propose a
  static screening scanner and dual-view consistency checks.
  https://arxiv.org/abs/2606.15020 (mechanism details read from https://arxiv.org/pdf/2606.15020)
- Office files: 31 channels diverge between human view and extractors (19 show content a
  human cannot see: 10 PPTX, 4 DOCX, 5 XLSX). Hidden text appears in 7% of ordinary Word
  documents, off-slide text in 5% of presentations, speaker notes in 71% of
  presentations, footers in 56% of Word documents. https://arxiv.org/pdf/2611.05806
- Seen in search results, not read in full: https://arxiv.org/pdf/2607.19396 (CrackedPDFs),
  https://arxiv.org/pdf/2505.16957 (malicious fonts), https://arxiv.org/pdf/2508.20863
  (peer-review injection), https://arxiv.org/pdf/2511.01287 ("Give a Positive Review Only").

## 2. Techniques

### T1. White-on-white / matching-colour text (PDF, docx, pptx)
- What: text painted in the page background colour; PhantomLint calls it the most common
  method. https://arxiv.org/html/2508.17884v2
- Placed: a sentence in the body or after the last visible line; in Word a run with white
  `w:color`; in PDF a fill-colour operator before the text.
- Source: https://arxiv.org/html/2508.17884v2 ; the Office paper treats a run as invisible
  when its colour matches the page background (white text on a coloured page is kept):
  https://arxiv.org/pdf/2611.05806

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Partial-good | PDF: inflate content streams (zlib), track fill colour (`rg`/`g`/`k`) around `BT..ET`; flag shown text while fill is `1 1 1 rg` or `1 g` (or all channels >= ~0.95). Real background unknown without drawing (coloured shapes make white text legit). docx: parse `word/document.xml` + `word/styles.xml`; flag `w:color w:val="FFFFFF"` / near-white, and `w:shd` fill equal to text colour, on runs with text; theme colours need resolving. pptx: `a:srgbClr` in `a:rPr`. |
| (b) | Surfaces text, no warning | Extractors return it as ordinary text; no marker. ffmpeg: n/a for documents. |
| (c) | Misses it, hence the diff | Render shows nothing; value is "extracted text has a sentence the image lacks". |

### T2. Tiny / near-zero font size
- What: text at ~0.1-1 pt or scaled to nothing. Sources: https://arxiv.org/html/2508.17884v2 ;
  split-view EG07 "near-zero font" https://arxiv.org/pdf/2606.15020 ; CSO lists ultra-small
  fonts https://www.csoonline.com/article/4053107/ai-prompt-injection-gets-real-with-macros-the-latest-hidden-threat.html
- Placed: between lines, page foot, or as a dot-sized run.

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Good | PDF: `/F1 N Tf` with N below a threshold (suggest < 3 pt) followed by shown text; effective size = Tf size x `Tm`/`cm` scale (also zero-height). docx: `w:sz`/`w:szCs` (half-points) < 6 on runs with text. pptx: `sz` (hundredths of pt) < 300 on `a:rPr`. Threshold is a judgement call. |
| (b) | Text yes, size lost | markitdown returns the text only. |
| (c) | Only if legible | Near-zero text renders as a smudge or nothing; subagent can note a faint line vs a sentence in the text layer. |

### T3. Invisible render mode (PDF `Tr 3`, also clip mode `Tr 7`, zero opacity)
- What: glyphs drawn with neither fill nor stroke; selectable and extractable but unseen.
  Legit use: OCR text layer over a scan. Sources: PhantomLint (mode 3, zero-opacity text)
  https://arxiv.org/html/2508.17884v2 ; split-view EG04 (Tr=3) and EG11 (Tr=7 text as clip)
  https://arxiv.org/pdf/2606.15020 ; mode 3 = invisible in library docs
  https://docs.rs/oxidize-pdf/1.2.1/src/oxidize_pdf/text/mod.rs.html ; a poppler post cites the
  PDF 32000-1:2008 text section (spec text itself not read)
  https://lists.freedesktop.org/archives/poppler/2018-June/013222.html

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Good, one caveat | Regex content streams for `3 Tr` / `7 Tr` preceding `Tj`/`TJ`; zero opacity via `gs` with `/ca 0` or `/CA 0` in ExtGState. Caveat: OCR'd scans use Tr 3 on every page; flag only when the page is not an image-only scan or when the text is instruction-like. |
| (b) | Surfaces it | Extractors return it as normal text. |
| (c) | Misses it, hence the diff | For OCR-layer PDFs the render shows the scan's own text, so the diff is empty (correct). |

### T4. Text outside the page box (MediaBox/CropBox) or off-slide
- What: text positioned beyond the visible page, or outside the CropBox. MediaBox/CropBox
  are page-object entries (Table 30; mirror https://github.com/p6-pdf/PDF-Specification-p6).
  PhantomLint "offpage text" https://arxiv.org/html/2508.17884v2 ; split-view EG06
  https://arxiv.org/pdf/2606.15020 ; off-slide text in 5% of ordinary decks
  https://arxiv.org/pdf/2611.05806
- Placed: negative or oversize x/y; pptx shape offset beyond slide size.

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Moderate | PDF: read `/MediaBox` and `/CropBox` from page dicts (object streams need zlib inflate), track `Tm`/`Td`/`cm` positions of shown text; flag outside CropBox (else MediaBox). pptx: `p:sldSz` vs `a:off`/`a:ext` in `ppt/slides/slideN.xml`; flag text shapes wholly outside. |
| (b) | Surfaces it | Extractors return it; markitdown exposes off-slide pptx text (per the Office paper). |
| (c) | Misses it, hence the diff | Rendering crops to the box. |

### T5. Text under images / covered by shapes; zero-area clipping
- What: text drawn first, then an opaque image or rectangle over it; or text inside a
  degenerate clip. Sources: "Obscured text", "Zero-area clipping" in
  https://arxiv.org/html/2508.17884v2 ; occlusion and clipping geometry in
  https://arxiv.org/pdf/2606.15020

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Weak | Geometry only: a filled `re` or image `Do` bbox containing an earlier text position; needs full graphics-state tracking, many false positives (text over a background picture). Degenerate clip (`W n` after a zero-size `re`) is easy to regex. |
| (b) | Surfaces text | Appears in extraction. |
| (c) | Best fit | Rendered image lacks the covered sentence. |

### T6. Invisible and control characters (zero-width, bidi, Unicode tags)
- What: characters that render as nothing. Unicode Tags block U+E0000-U+E007F mirrors ASCII;
  the payload is text written in that block. Cisco: strip with
  `0xE0000 <= ord(ch) <= 0xE007F` (may remove legitimate flag emoji):
  https://blogs.cisco.com/ai/understanding-and-mitigating-unicode-tag-prompt-injection
  AWS guidance on character smuggling (sanitisation pitfalls such as surrogate pairs came
  from a search summary; page body did not load):
  https://aws.amazon.com/blogs/security/defending-llm-applications-against-unicode-character-smuggling
- Bidi controls (UAX #9): LRE U+202A, RLE U+202B, PDF U+202C, LRO U+202D, RLO U+202E,
  LRI U+2066, RLI U+2067, FSI U+2068, PDI U+2069; marks LRM U+200E, RLM U+200F, ALM U+061C.
  https://www.unicode.org/reports/tr9/ . Reordering-for-deception is documented for source
  code (CVE-2021-42574): https://trojansource.codes/ . Use inside assignment documents:
  `[unverified]`. Zero-width code points (U+200B/C/D, U+2060, U+FEFF) and the Cf/Co/Cs
  categories: standard Unicode knowledge, `[unverified]` against a fetched page.

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Excellent | `unicodedata.category(ch)` in {Cf, Co, Cs}; explicit ranges U+E0000-E007F, U+202A-202E, U+2066-2069, U+200B-200F, U+2060-2064, U+FEFF (except one BOM at file start), variation selectors U+FE00-FE0F and U+E0100-E01EF. Decode tag chars (`chr(ord(c)-0xE0000)`) only to show the student what they say. Legit: Hebrew/Arabic/Persian text uses LRM/RLM/ZWNJ; flag by count and context, not presence. Run on docx XML text and decoded PDF strings. |
| (b) | Unknown | Pass-through or drop not confirmed; do not rely on it. `[unverified]` |
| (c) | Blind | Page looks normal. |

### T7. PDF metadata, annotations, form fields, optional-content layers
- What: instruction text where readers do not look: Info dictionary, XMP, annotation
  `/Contents` (comments), AcroForm field values, Optional Content Groups set OFF. CSO lists
  file metadata (DOCX custom properties, PDF XMP, EXIF) as carriers
  https://www.csoonline.com/article/4053107/ai-prompt-injection-gets-real-with-macros-the-latest-hidden-threat.html ;
  PhantomLint lists OCGs set to /OFF https://arxiv.org/html/2508.17884v2 ; split-view covers
  optional-content visibility https://arxiv.org/pdf/2606.15020 . Annotations and form fields
  specifically as carriers: `[unverified]` (spec sections 12.5 and 7.8 not fetched).

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Good for presence | Regex objects: `/Subtype /Text`, `/FreeText`, `/Popup` with `/Contents (...)`; `/AcroForm` with `/V`; `/Info` keys (`/Title /Subject /Keywords /Author`); `<x:xmpmeta` packet; `/OCProperties` with `/OFF [`. Strings may be hex or UTF-16BE (`<FEFF...>`); decode. `/ObjStm` needs zlib inflate. Flag long or imperative text. |
| (b) | Probably not surfaced | Many extractors ignore annotations/metadata; per tool and version `[unverified]`. |
| (c) | Blind | Not on the page. |

### T8. Text layer differs from what is drawn (font remap, ToUnicode, ActualText)
- What: glyph shapes show one thing, character codes / `/ToUnicode` / `/ActualText` say
  another. A `/ToUnicode` CMap can map a code to any string; `/ActualText` on a
  marked-content span makes extractors substitute its value; a Type 3 font without
  `/ToUnicode` forces extractor guessing. https://arxiv.org/pdf/2606.15020 . Malicious
  fonts mapping characters to blank glyphs: named in PhantomLint
  https://arxiv.org/html/2508.17884v2 and studied in https://arxiv.org/pdf/2505.16957
  (body not readable by the fetch tool).

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Presence only | Flag `/ActualText` (rare in student material, good signal), `/ToUnicode` CMaps whose bfchar/bfrange map to unrelated Latin letters, embedded fonts lacking `/ToUnicode`, many Private Use (Co) characters in extracted text. Cannot prove glyph shapes without rasterising. |
| (b) | Shows the AI view | Extraction returns the text-layer version, i.e. the hidden text. |
| (c) | Core detector | Render, read the image, compare with extraction. The paper recommends dual-view consistency; PhantomLint's OCR consistency test is the same idea. |

### T9. docx hidden runs, comments, tracked changes, alt text, headers/footers, text boxes, custom XML
- Hidden run: `<w:rPr><w:vanish/></w:rPr>`; ISO/IEC 29500 (quoted by Microsoft): contents
  "shall be hidden from display"; toggle property; applications may force-show hidden text.
  https://learn.microsoft.com/en-us/office/open-xml/word/how-to-remove-hidden-text-from-a-word-processing-document
  A `w:vanish` run and image alt text are shown as injection carriers invisible in the default
  view in https://arxiv.org/pdf/2611.05806 , which also finds DOCX extractors mostly omit
  headers, footers, footnotes, text boxes, content controls, tracked insertions (so the AI
  can miss text the human sees; see T12).
- Other zip parts: `word/comments.xml`, `w:ins`/`w:del`, `wp:docPr descr=`/`title=` (alt
  text), `word/header*.xml`, `word/footer*.xml`, `word/footnotes.xml`, `w:txbxContent`,
  `customXml/*.xml`, `docProps/core.xml`, `docProps/custom.xml`. Their use as assignment traps:
  `[unverified]`.

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Excellent | `zipfile` + `xml.etree`: `w:vanish` in `w:rPr` or in styles (resolve `w:rStyle`/`w:pStyle`; ignore `w:val` of 0/false/off); `w:color`, `w:sz` as T1/T2; `w:highlight`/`w:shd` equal to text colour; list comments, alt text, tracked changes, headers/footers, text boxes, customXml, custom properties; report text per part. |
| (b) | Partial `[unverified]` | markitdown on docx hidden runs, comments, alt text not confirmed. |
| (c) | Complementary | Render docx to PDF/images (e.g. LibreOffice): vanish and white text disappear; diff vs docx text. |

### T10. pptx and xlsx equivalents (brief)
- pptx: speaker notes (`ppt/notesSlides/`), hidden slides (`show="0"` on `p:sld`),
  off-slide shapes, alt text (`descr` on `p:cNvPr`), shape names, masters. markitdown alone
  exposes nine invisible PPTX channels (off-slide text, hidden slides, speaker notes, alt
  text, shape names, slide masters among them). https://arxiv.org/pdf/2611.05806
- xlsx: hidden sheets (`state="hidden"`/`veryHidden` in `xl/workbook.xml`), hidden rows and
  columns, defined names, cell comments (`xl/commentsN.xml`), number formats that change the
  displayed value (7% of spreadsheets differ materially). Same paper. The attribute names
  `show="0"` and `state="hidden"` are from my knowledge of the formats, `[unverified]`.

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Good | zipfile + xml: the parts and attributes above; flag long text in notes, comments, hidden sheets, alt text, off-slide shapes. |
| (b) | Surfaces many | markitdown includes notes, hidden-slide text, hidden sheets/rows (per paper); adds no warning. |
| (c) | Partial | Render slides (needs LibreOffice); off-slide and notes absent; diff vs extraction. |

### T11. The instruction sentence itself ("if you are an AI...", "include the word Y")
- What: the payload is a sentence addressed to an assistant; it may even be visible.
  PhantomLint pairs a phrase detector (sentence-transformer vs known phrases such as
  "ignore all previous instructions") with the OCR diff, because text analysis alone cannot
  tell visible from hidden. https://arxiv.org/html/2508.17884v2 (the "incapable" wording is from
  a search summary of https://arxiv.org/html/2508.17884v1, not read directly).

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Good as a flag | Case-insensitive regex over text from every channel: `(if|when) you are (an? )?(ai|llm|language model|chatgpt|assistant)`, `ignore (all )?(previous|prior|above) instructions`, `as an ai`, `do not (mention|reveal|tell)`, `include the (word|phrase)`, `begin (your )?(answer|response) with`, `system prompt`; add Hebrew phrasings for Hebrew courses. Patterns are my suggestions, not from a source. Rank: hit in a hidden channel = high; visible = informational. |
| (b) | Surfaces text | Run the same regex over markitdown output. |
| (c) | Reads meaning | Judges whether a visible sentence addresses an AI or conflicts with the task. |

### T12. Honeypots and contradictions (semantic)
- What: made-up term, step or citation only a model following the trap would use; a
  requirement contradicting the rubric; numbers/deadlines differing between places in a
  file or between file and course site. The "Madagascar" canary is this class (an out-of-topic
  word). https://www.ibtimes.co.uk/professors-ingenious-trap-exposes-ai-cheating-1811438
  Contradictory numbers and file-vs-course-site mismatch as a deliberate trap, and fake
  citation honeypots: no source found `[unverified]`. Related: extractors can drop visible
  content (headers, footers, footnotes, text boxes), so a model may read a different
  assignment than the human. https://arxiv.org/pdf/2611.05806

| Detector | Verdict | How |
|---|---|---|
| (a) stdlib | Limited | Collect numbers near keywords (`due`, `weight`, `%`, `points`, `words`, `pages`, dates) per part/channel and report mismatches (20% in body vs 25% in footer). Report terms present only in hidden channels. File-vs-site comparison only if the tool already holds the site copy. |
| (b) | Text only | No semantic check. |
| (c) | Judgement | Flags statements that contradict the rubric or look like a trap; cannot prove intent. |

## 3. Summary matrix

Y = reliably flags; P = partial / heuristic; S = surfaces text but no warning; N = cannot.

| Technique | (a) stdlib | (b) ffmpeg / markitdown | (c) visual-read |
|---|---|---|---|
| T1 white / matching colour | Y (P if background unknown) | S | Y via diff |
| T2 tiny font | Y (threshold) | S | P |
| T3 Tr 3 / Tr 7 / zero alpha | Y (watch OCR scans) | S | Y via diff |
| T4 off-page / off-slide | P (geometry) | S | Y via diff |
| T5 covered / zero clip | P (weak) | S | Y via diff |
| T6 invisible chars (tags, ZW, bidi) | Y | `[unverified]` | N |
| T7 PDF metadata, annots, forms, OCG off | Y (presence) | mostly not surfaced `[unverified]` | N |
| T8 ToUnicode / ActualText / font remap | P (mechanism presence) | S (shows AI view) | Y (core) |
| T9 docx hidden runs, comments, alt, tracked, customXml | Y | P `[unverified]` | P |
| T10 pptx / xlsx hidden channels | Y | S (pptx notes, hidden slides) | P |
| T11 "if you are an AI" sentence | Y (regex flag) | S, then regex | Y (meaning) |
| T12 honeypot / contradiction | P (numbers) | N | P (judgement) |

Suggested order: (1) stdlib scan of all channels and invisible characters; (2) for each
hit, render and let visual-read confirm what a human sees; (3) T11 regex over hidden and
visible text; (4) report. Dual-view comparison is the literature's recommended defence
https://arxiv.org/abs/2606.15020 and PhantomLint's basis https://arxiv.org/html/2508.17884v2 .

## 4. Likelihood in a real university assignment (my judgement)
Based on reported educator practice (white text, odd canary word) and the innocent-baseline
prevalence of hidden constructs in Office files:
1. T1 white-on-white sentence (docx or PDF): the documented educator method.
2. T2 tiny-font variant of the same.
3. T9 docx `w:vanish` run, alt text, or header/footer text.
4. T11 visible or semi-visible "if you are an AI" sentence.
5. T12 canary term, or a requirement conflicting with the rubric.
T3, T4, T6, T8 need more skill; frequency in course files unmeasured `[unverified]`.

## 5. What the student should be told (plain words)
- Hidden instruction found: "This file has text you cannot see on screen. It is written
  for an AI assistant and asks it to: <quote>. Where: <page/part>. Your assistant will not
  follow it. It may be a deliberate check by the lecturer."
- Hidden but harmless: "This file has hidden text (<quote>). It looks like a leftover or
  formatting artifact, not an instruction."
- Contradiction: "The file says <A> here and <B> there. Check the course site or ask the
  lecturer which is right."
- Always: say what is there and where; do not accuse anyone; the student decides what to do
  under their institution's AI rules. A finding is not proof of the lecturer's intent, and
  "nothing found" means only "nothing found by these checks".

## 6. Could not verify
Claims without a fetched primary source:
- PDF spec normative wording for `Tr` modes, annotation `/Contents`, AcroForm, OCG (spec not
  fetched; only a mirror table of page entries and secondary mentions).
- Annotations, form fields or XMP used as injection carriers in assignments (CSO mentions
  PDF/XMP metadata and DOCX custom properties generally).
- docx comments, tracked changes, custom XML, headers/footers used as educator traps. The
  Office paper lists several as extractor-divergence channels; I read it via pdftotext
  excerpts, not in full.
- Bidi and zero-width characters inside assignment documents (Trojan Source is about source
  code); exact zero-width code points and Cf/Co/Cs rules not fetched (UAX #9 fetched for bidi
  controls only, first 100k characters).
- markitdown and ffmpeg behaviour on docx hidden runs, comments, PDF annotations, metadata,
  invisible characters. ffmpeg has no document support; for images only frame extraction is
  plausible; nothing sourced. markitdown OCR default: unverified.
- OOXML attribute names `show="0"` (hidden slide) and `state="hidden"` (hidden sheet).
- Trojan-horse detail beyond the IBTimes article (TechSpot, Chronicle returned 403; counts
  such as "32 of 35" are search-snippet only).
- Contradictory numbers between file and course site as a deliberate trap; fake-citation
  honeypots: no source found.
- AWS blog's surrogate-pair point (page body did not load).
- Papers 2505.16957, 2511.01287, 2508.20863, 2607.19396: only titles/summaries seen.
- Prevalence of each technique in real course files: unmeasured.

Limits of detection:
- Rendered but tiny, low-contrast or camouflaged text (#fefefe on white, text over a
  pattern): a static scan sees a colour near the background; visual-read may not see it.
  PhantomLint needed blur on low-contrast regions and still had OCR failures on very small
  fonts. https://arxiv.org/html/2508.17884v2
- Text inside images (a screenshot of an instruction): needs OCR or vision; stdlib cannot.
- Visible instructions: content alone cannot say visible vs hidden; channel and render
  comparison decide.
- Semantic honeypots (made-up term, rubric contradiction): no static scan proves intent;
  only candidates can be flagged.
- Pure-stdlib PDF parsing is incomplete (encryption, object streams, incremental updates,
  LZW/ASCII85/DCT filters, Type 3 fonts, inherited page boxes). Report "could not fully
  parse", never "clean".
- OCR-layer scans legitimately use invisible text: false positives on Tr 3.
- High innocent baseline (hidden text in 7% of Word docs, notes in 71% of decks,
  https://arxiv.org/pdf/2611.05806): warn on instruction-like content, not mere presence.
