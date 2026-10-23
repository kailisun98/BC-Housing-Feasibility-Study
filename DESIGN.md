---
name: Funding-Fit Memo
description: A well-set memo with a form beside it; paper, ink, one blue for what you can touch, status always in words.
colors:
  paper: "#FAF9F6"
  ink: "#1B1B1A"
  memo-grey: "#6B6B66"
  hairline: "#E4E2DC"
  card: "#FFFFFF"
  field-border: "#D6D3CC"
  deep-blue: "#1D4ED8"
  selection-blue: "#CFDCF7"
  cool-desk: "#EEF2F8"
  cool-desk-line: "#DDE4EF"
  sand: "#F3EFE6"
  sand-line: "#E6DFCF"
  pass: "#15803D"
  conditional: "#B45309"
  fail: "#B91C1C"
  uncertain: "#6D28D9"
  not-applicable: "#6B7280"
  info: "#1D4ED8"
  pass-ink: "#146C35"
  conditional-ink: "#9A4607"
  fail-ink: "#A31818"
  uncertain-ink: "#5B21B6"
  pass-wash: "#EDF6EF"
  conditional-wash: "#FBF3E7"
  fail-wash: "#FBEEED"
  uncertain-wash: "#F3F0FA"
  wash-grey: "#5E5D66"
  proposed-blue: "#2F6FED"
  proposed-blue-line: "#1E40AF"
  outright-grey: "#C9CED6"
  outright-grey-line: "#6B7280"
  night-paper: "#141311"
  night-ink: "#ECEAE4"
  night-card: "#1D1C19"
  night-blue: "#8FB0FF"
typography:
  display:
    fontFamily: "Fraunces, Newsreader, Georgia, serif"
    fontSize: "40px"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "-0.005em"
  verdict:
    fontFamily: "Fraunces, Newsreader, Georgia, serif"
    fontSize: "28px"
    fontWeight: 500
    lineHeight: 1.25
  headline:
    fontFamily: "Fraunces, Newsreader, Georgia, serif"
    fontSize: "20px"
    fontWeight: 500
    lineHeight: 1.3
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
  eyebrow:
    fontFamily: "IBM Plex Mono, JetBrains Mono, ui-monospace, monospace"
    fontSize: "11px"
    fontWeight: 500
    letterSpacing: "0.08em"
  mono:
    fontFamily: "IBM Plex Mono, JetBrains Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  control: "6px"
  card: "8px"
  region: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "22px"
  xxl: "28px"
components:
  button-primary:
    backgroundColor: "{colors.deep-blue}"
    textColor: "{colors.card}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
  button-secondary:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "7px 14px"
  status-pill:
    backgroundColor: "{colors.uncertain}"
    textColor: "{colors.card}"
    typography: "{typography.eyebrow}"
    rounded: "{rounded.pill}"
    padding: "2px 9px"
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "{spacing.xl}"
  answer-card-uncertain:
    backgroundColor: "{colors.uncertain-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "{spacing.xl}"
  input:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "7px 10px"
---

# Design System: Funding-Fit Memo

## Overview

**Creative North Star: "The Careful Memo"**

The product is a memo, and the interface is the desk it sits on. Everything the reader sees is set
like a document someone took trouble over: warm paper rather than white, a serif voice for the
sentences a person would say aloud, a sans for the working parts, and a monospace whisper for the
things a machine wrote down, stamps, rule ids, section eyebrows. The page is calm and unhurried.
One idea per card, hairlines instead of boxes, and nothing that moves unless a run has just landed.

Colour is meaning, never decoration. Six status hues exist only to say pass, conditional, fail,
uncertain, not applicable or info, and the same hue that marks a status word also tints the card
that carries the answer. One deep blue belongs to the things you can touch: the Run button, the
step you are on, links, focus, the caret. Three regions tell the reader where they are: the cool
pane where facts are entered, the paper where the memo is read, and the sand band where it leaves
for a file or for Revit. The massing drawings keep their own three tones, blue for proposed, grey
for outright, amber for the staff benchmark, because those are the memo's own figures.

Two things it is not, confirmed: not a dashboard (no gauges, KPI tiles, charts for their own sake,
no icon-and-heading cards as page structure) and not a startup landing page (no gradients, glass,
hero numbers, floating shadows or marketing voice).

**Key Characteristics:**
- Three voices: serif for human sentences, sans for the interface and body, mono for stamps and labels.
- Paper and ink first; dark mode is composed from warm near-black, not inverted.
- Status is always a word; its colour only accompanies it.
- One accent, deep blue, for interactive elements only.
- Flat surfaces separated by hairlines; the only shadow belongs to the walkthrough card.
- Cards wear a faint wash in the hue of the answer they give.

## Colors

A warm neutral page with one working blue, six semantic hues that never leave their job, and three
quiet regions.

### Primary
- **Deep Blue** (`{colors.deep-blue}`): the one interactive colour. The Run button, the active and
  completed step marks, link text and underlines, the ledger's layer toggles, the focus ring, the
  caret, and the eyebrows inside the input cards. In dark mode it lightens to **Night Blue**
  (`{colors.night-blue}`) on near-black ink.
- **Selection Blue** (`{colors.selection-blue}`): text selection only.

### Secondary
The six status hues, used only for status, as pill backgrounds under white text and as the ink of
a verdict word and its eyebrow:
- **Pass** (`{colors.pass}`), **Conditional** (`{colors.conditional}`), **Fail** (`{colors.fail}`),
  **Uncertain** (`{colors.uncertain}`), **Not applicable** (`{colors.not-applicable}`),
  **Info** (`{colors.info}`).
- As text on a wash they deepen slightly: **Pass Ink**, **Conditional Ink**, **Fail Ink**,
  **Uncertain Ink** (`{colors.pass-ink}` to `{colors.uncertain-ink}`), each clearing 7:1 on its wash.
- As the wash of an answer card: **Pass Wash**, **Conditional Wash**, **Fail Wash**, **Uncertain
  Wash** (`{colors.pass-wash}` to `{colors.uncertain-wash}`), with secondary text in **Wash Grey**
  (`{colors.wash-grey}`) rather than the page grey.

### Tertiary
The massing figures' own tones, fixed by the drawings and never used elsewhere:
- **Proposed Blue** (`{colors.proposed-blue}`, line `{colors.proposed-blue-line}`) at 35% fill.
- **Outright Grey** (`{colors.outright-grey}`, line `{colors.outright-grey-line}`).
- The staff benchmark is drawn in **Conditional** amber, dashed.

### Neutral
- **Paper** (`{colors.paper}`): the page.
- **Card** (`{colors.card}`): every card and field; the memo's sheets.
- **Ink** (`{colors.ink}`): headings, body text, verdict sentences.
- **Memo Grey** (`{colors.memo-grey}`): the second sentence of a finding, labels, captions, eyebrows.
- **Hairline** (`{colors.hairline}`): every separator, card border and table rule.
- **Field Border** (`{colors.field-border}`): inputs, selects and secondary buttons.
- **Cool Desk** (`{colors.cool-desk}`, line `{colors.cool-desk-line}`): the input region behind the
  site and option cards.
- **Sand** (`{colors.sand}`, line `{colors.sand-line}`): the Export band at the foot of the memo.
- **Night Paper**, **Night Ink**, **Night Card** (`{colors.night-paper}`, `{colors.night-ink}`,
  `{colors.night-card}`): the dark theme's page, text and sheets.

### Named Rules
**The Status-Only Rule.** A status hue appears only where a status word is printed or where a card
carries that status. It never colours a button, a heading, a chart or a decoration.

**The One Hand Rule.** Deep blue marks what the reader can act on and nothing else. If an element is
blue, it can be clicked or typed into.

**The Written Word Rule.** Colour accompanies a status; it never carries it alone. Every pill, verdict
and chip prints its word.

## Typography

**Display Font:** Fraunces (with Newsreader, then Georgia)
**Body Font:** Inter (with the system UI stack)
**Label/Mono Font:** IBM Plex Mono (with JetBrains Mono, then ui-monospace)

**Character:** A serif with some warmth for the sentences a person would read aloud, a plain sans
that disappears into the interface, and a monospace that marks what the machine recorded. Italic
serif is the single accent inside a verdict: "By rezoning: *not yet confirmed*."

### Hierarchy
- **Display** (500, 40px, 1.1): the memo's title, the site address. One per page.
- **Verdict** (500, 28px, 1.25): the answer sentence at the head of each of the three answer cards,
  with the operative word in italic and in the status hue.
- **Headline** (500, 20–24px, 1.2–1.3): card and section headings; answer-card headings sit in Memo
  Grey at weight 400 so the verdict beneath them leads.
- **Body** (400, 16px, 1.5): findings and prose. The first sentence of a finding is Ink, the rest
  Memo Grey. Measure kept under about 72ch by the two-pane layout.
- **Label** (500, 13px): form labels, buttons, table cells at 13–14px.
- **Eyebrow** (500, 11px mono, 0.08em tracking, uppercase): the section labels the brief fixed,
  "01 · IS IT ALLOWED", table headers, figure labels "FIG 01 · Plan", pill text.
- **Mono** (400, 12–13px): stamps, rule ids, hashes, numbers used, the Revit lines.

### Named Rules
**The Lead Sentence Rule.** In any finding, the first sentence is Ink and the continuation is grey.
Hierarchy inside a paragraph comes from colour, not weight.

**The Eyebrow Rule.** Section eyebrows are mono, 11px, uppercase, tracked 0.08em, and sit above a
serif heading. They are the brief's own device and stay.

## Layout

Two panes on a paper page: the inputs on the left in a cool region 340 to 420px wide, the memo on
the right taking the rest, with a 28px gutter and a 24px page margin, capped at 1880px. The top bar
(56px) and the step strip beneath it are sticky. Below 1100px the panes stack, the two input cards
sit side by side, and below 760px everything is one column. At 1600px and above the memo body
becomes two columns: the three answers and the rest of the memo on the left, the figures in a
440px column on the right; narrower, the figures sit between the answers and the ledger.

Rhythm is a 4px scale: 4, 6, 8, 10, 12, 14, 16, 20, 22, 24, 28. Cards carry 22px of padding and sit
16 to 20px apart. Forms are a single column with 14px between fields and 12px within a group; short
numeric fields share a row with a 10px gap. Density is calm: one idea per card, more space above a
heading than below it.

## Elevation & Depth

Flat. Surfaces are separated by 1px hairlines and by tone, never by shadow: white cards on paper,
paper against the cool desk and the sand band, the dark theme's cards a half-step lighter than its
page. The single exception is the walkthrough card, which floats over a dimmed page and carries an
offset, soft shadow because it is genuinely above everything.

### Shadow Vocabulary
- **Walkthrough card** (`box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22)`): only the guided-tour card,
  over the spotlight backdrop.

### Named Rules
**The Hairline Rule.** Depth is drawn, not cast. A card is a hairline and a change of tone; nothing
at rest has a shadow.

## Shapes

Gently rounded, consistently: controls and fields 6px, cards 8px, the two regions 12px, pills and
step marks fully round. Borders are 1px everywhere, hairline on cards and tables, field-border on
controls. No coloured side borders, no decorative strokes; the three-state control is a single
6px-rounded box whose chosen segment fills solid. Figures are drawn with 1px non-scaling strokes.

## Components

### Buttons
Quiet and exact; they say what they do.
- **Shape:** 6px radius, 1px border, 14px weight 500, 7px by 14px padding; small variant 3px by 9px at 12px.
- **Primary:** Deep Blue fill, white text, blue border. One per screen: Run the rules; the
  walkthrough's Next.
- **Secondary:** Card fill, Ink text, Field Border; the action bar's downloads and Print.
- **Quiet:** transparent fill, same border; Save as…, Copy, Back.
- **Hover / Focus:** border darkens to Ink; primary brightens 5%; focus is a 2px Deep Blue ring
  offset 2px. Disabled sits at 45% opacity and does not react.

### Status pills
- **Style:** status hue fill, white text, mono 11px uppercase tracked 0.04em, 2px by 9px, fully round.
- **State:** none; a pill is a printed word. Layer summaries show counts beside the word.

### Cards / Containers
- **Corner Style:** 8px.
- **Background:** Card; an answer card takes the wash of its verdict's status.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1px Hairline; input cards use the cool desk's line.
- **Internal Padding:** 22px; figures 18px.

### Inputs / Fields
- **Style:** 1px Field Border on Card, 6px radius, 7px by 10px, 14px text; labels 13px Memo Grey
  above, help text 12px below.
- **Focus:** 2px Deep Blue outline, 1px offset; caret Deep Blue.
- **Three-state control:** Yes / No / Not sure in one bordered box; the chosen segment fills Ink
  with paper text, except Not sure, which fills Uncertain purple, so the honest choice looks normal.
- **Checkbox groups and tree rows:** accent-coloured native checkboxes; compact 13px rows.

### Navigation
- **Step strip:** four uppercase 12px labels with a numbered circle; the current step is Deep Blue
  with a blue underline and a filled blue circle, completed steps keep a blue ring, the rest are
  Memo Grey. Sticky under the top bar; a "Walkthrough" link sits at its end.
- **Top bar:** wordmark in serif with an italic "Memo", the as-of date in a mono field, the primary
  button, then the stamp in a hairline-bordered mono chip with a Copy button.

### Answer cards
The signature component. Eyebrow in the status hue, a grey serif question, the verdict in 28px
serif with the operative word italic and coloured, then the findings in lead-and-continuation
prose or a pill-led list; the third card holds a hairline table of open items with a Who / what
column in Wash Grey. The card's wash and tone come from one `data-verdict` attribute.

### Figures
A card with a mono figure label, an SVG drawn in metres with non-scaling strokes, a mono legend
with swatches, and a 13px grey caption carrying the numbers. FIG 03 is the Revit sheet image when
one exists.

### Engine chip and toast
The chip is a fully round mono label that reads loading, ready or error in the matching status
hue; the toast is Ink on paper, bottom-centre, fades out on its own.

## Do's and Don'ts

### Do:
- **Do** print every status as a word and let its hue accompany it; a pill, a verdict word, a card wash.
- **Do** keep Deep Blue for things the reader can act on, and give the active step, links and focus that blue.
- **Do** set the memo's sentences in Fraunces at 40 / 28 / 20px and keep body Inter at 16px with 1.5 line height.
- **Do** separate surfaces with 1px hairlines and tone; keep cards at 8px radius and 22px padding.
- **Do** compose dark mode from Night Paper and Night Card with the lifted status inks; check every pair stays above 4.5:1.
- **Do** keep the figures' three tones, blue proposed, grey outright, amber benchmark, exactly as drawn.

### Don't:
- **Don't** build a dashboard: no gauges, KPI tiles, sparklines, or icon-plus-heading cards as structure.
- **Don't** reach for a landing page's kit: no gradients, glass, hero numbers, floating shadows, marketing voice.
- **Don't** put a status hue on a button, a heading, a chart or a background that carries no status.
- **Don't** add a second accent, a coloured side border, or a shadow on anything that is not the walkthrough card.
- **Don't** animate anything but the 150ms fade when a run lands and the walkthrough spotlight's fade; honour reduced motion.
- **Don't** use "N/A", icons in place of words, or a checkbox where "not sure" is a legitimate answer.
