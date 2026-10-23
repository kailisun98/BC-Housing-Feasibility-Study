---
name: Funding-Fit Memo
description: A compact drafting tool in the Lotwise language; slate ink on a cool grey page, white panels, dark buttons, statuses as marked words, drawings on white paper.
colors:
  ink: "#2C3E50"
  muted: "#5F6672"
  page: "#F5F6F8"
  panel: "#FFFFFF"
  line: "#E1E5EA"
  field: "#FFFFFF"
  group: "#E9EEF4"
  blue: "#2A6FB8"
  amber: "#C77D14"
  red: "#C81E1E"
  ok: "#2F7D4A"
  warn: "#D9A520"
  teal: "#2A9D8F"
  on-warn: "#1F2933"
  pass-text: "#246A3D"
  conditional-text: "#7A5A00"
  fail-text: "#A81A1A"
  uncertain-text: "#8F5A0E"
  info-text: "#245F9C"
  not-applicable: "#8A93A0"
  status-info: "#EAF0F8"
  status-busy: "#FFF1D6"
  status-ok: "#E1F2E5"
  status-error: "#FBE1E1"
  paper: "#FFFFFF"
  envelope-blue: "#3C8CDC"
  street-grey: "#8E8E8E"
  lane-grey: "#BDBDBD"
  draw-ink: "#1F2933"
  draw-muted: "#5F6672"
  draw-note: "#7A5A00"
  night-ink: "#E6EBF1"
  night-muted: "#9AA4B1"
  night-page: "#14181D"
  night-panel: "#1C2128"
  night-line: "#2C343D"
  night-field: "#12161B"
  night-group: "#232C37"
  night-blue: "#5AA2EA"
  night-amber: "#E0A03A"
  night-red: "#E0554F"
  night-ok: "#4CAE6D"
  night-warn: "#E0B43A"
typography:
  title:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  wordmark:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  heading:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.35
  body:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  small:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
  key:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.06em"
  table:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "11.5px"
    fontWeight: 400
    lineHeight: 1.45
  mono:
    fontFamily: "IBM Plex Mono, SF Mono, Menlo, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.5
  stamp:
    fontFamily: "IBM Plex Mono, SF Mono, Menlo, Consolas, monospace"
    fontSize: "11.5px"
    fontWeight: 600
    letterSpacing: "0.08em"
rounded:
  mark: "2px"
  control: "4px"
  button: "5px"
  panel: "6px"
  card: "8px"
  pill: "10px"
  round: "50%"
spacing:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "14px"
  xxl: "16px"
  xxxl: "20px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.panel}"
    typography: "{typography.body}"
    rounded: "{rounded.button}"
    padding: "6px 12px"
  button-secondary:
    backgroundColor: "{colors.group}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.button}"
    padding: "6px 12px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.button}"
    padding: "6px 12px"
  status-pill:
    backgroundColor: "{colors.status-busy}"
    textColor: "{colors.uncertain-text}"
    typography: "{typography.key}"
    rounded: "{rounded.pill}"
    padding: "2px 8px 2px 3px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  answer-card-uncertain:
    backgroundColor: "{colors.status-busy}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  input:
    backgroundColor: "{colors.field}"
    textColor: "{colors.ink}"
    typography: "{typography.small}"
    rounded: "{rounded.control}"
    padding: "5px 8px"
  status-strip:
    backgroundColor: "{colors.status-info}"
    textColor: "{colors.ink}"
    typography: "{typography.small}"
    padding: "6px 16px"
---

# Design System: Funding-Fit Memo

## Overview

**Creative North Star: "The Drafting Tool"**

The memo is produced by a tool, and the tool looks like one: the same language as Kai's Lotwise
massing app, which is the pinned precedent. One sans, IBM Plex Sans at 13px, does nearly all the
talking; IBM Plex Mono is reserved for what a machine wrote down, stamps, rule ids, hashes, paths
and the lines to paste into a shell. Slate ink on a cool grey page, with white panels separated by
a 1px line and a whisper of shadow. Corners are small, 4 to 6px, and buttons are dark ink that
lifts on hover and sinks on press. Nothing is decorative; the page is dense the way a good
drawing set is dense, and it stays calm because every element has a fixed job.

Colour is meaning. Blue is for links, focus, the selection and the step you are on; amber is for
what is pending, the "not sure" answer, the engine still loading, a benchmark line; green, yellow,
red, blue and grey mark the six statuses, always beside the printed word, never instead of it.
The status strip under the step bar carries one line of feedback for every action, with a dot that
says info, busy, ok or error. The massing drawings sit on white paper in both themes and keep
Lotwise's drawing tones: envelope blue for the proposed mass, lane grey for the outright one, a
red dashed line for the setback envelope, amber dashes for the staff benchmark.

Two things it is not, confirmed: not a dashboard (no gauges, KPI tiles, charts for their own sake,
no icon-and-heading cards as page structure) and not a startup landing page (no gradients, glass,
hero numbers, floating shadows or marketing voice).

**Key Characteristics:**
- One sans at 13px with 11px uppercase keys; mono only for machine-written text.
- Slate ink, cool grey page, white panels; dark mode is the same tool at night, not an inversion.
- Buttons are ink-filled; the secondary ones take the group grey. Hover lifts, press sinks 1px.
- A status is a word on a tinted pill with a round mark and a glyph before it.
- Numbered badges stand in for section numbers; step panels and answer cards share them.
- Drawings are always on white paper, whatever the theme.

## Colors

A cool neutral set, one working blue, amber for the pending, five status tints that stay beside
their words, and the drawings' own tones.

### Primary
- **Blue** (`{colors.blue}`): links, the focus ring, the caret, the selection tint at 28%, the
  status strip's resting dot and the Info status mark. In dark mode it lifts to **Night Blue**
  (`{colors.night-blue}`).
- **Ink** (`{colors.ink}`): text, the primary button, the chosen segment of a three-state control,
  the filled badge of the current and completed steps, the rule over a title block.

### Secondary
- **Amber** (`{colors.amber}`): what is pending or unsettled, the "Not sure" segment when chosen,
  the engine chip while loading, the uncertain status mark, the dirty-form note, the staff
  benchmark line in the section.
- The status marks: **OK** (`{colors.ok}`) for pass, **Warn** (`{colors.warn}`) for conditional,
  **Red** (`{colors.red}`) for fail, **Amber** for uncertain, **Not applicable** grey
  (`{colors.not-applicable}`), **Blue** for info. Each mark carries a glyph on a 14px circle.
- The status washes, shared with the strip and the answer cards: **Status OK**
  (`{colors.status-ok}`), **Status Busy** (`{colors.status-busy}`, also conditional and uncertain),
  **Status Error** (`{colors.status-error}`), **Status Info** (`{colors.status-info}`), and the
  group grey for not applicable. Text on a wash uses the matching deepened ink, **Pass Text** to
  **Info Text** (`{colors.pass-text}`, `{colors.conditional-text}`, `{colors.fail-text}`,
  `{colors.uncertain-text}`, `{colors.info-text}`), each clearing 4.5:1 on its wash in both themes.

### Tertiary
The drawings' tones, fixed in both themes because the paper is always white:
- **Paper** (`{colors.paper}`): the figure card and the Revit sheet image.
- **Envelope Blue** (`{colors.envelope-blue}`): the proposed mass at 50% fill, line Blue.
- **Lane Grey** (`{colors.lane-grey}`): the outright mass, line **Street Grey** (`{colors.street-grey}`).
- **Draw Ink** (`{colors.draw-ink}`) and **Draw Muted** (`{colors.draw-muted}`): the lot line,
  labels and captions; **Draw Note** (`{colors.draw-note}`): a caveat under a figure.
- The setback envelope is a red dashed line; the staff benchmark an amber one.

### Neutral
- **Page** (`{colors.page}`): the page and the input rail.
- **Panel** (`{colors.panel}`): the top bar, step bar, every card, the tour card.
- **Field** (`{colors.field}`): inputs, selects, the code blocks.
- **Line** (`{colors.line}`): every border and table rule.
- **Group** (`{colors.group}`): secondary buttons, the active step, badges, the not-applicable wash.
- **Muted** (`{colors.muted}`): labels, keys, captions, the continuation of a finding.
- The night set, **Night Ink** to **Night Warn**: the same roles at night; page `{colors.night-page}`,
  panel `{colors.night-panel}`, line `{colors.night-line}`, field `{colors.night-field}`, group
  `{colors.night-group}`.

### Named Rules
**The Marked Word Rule.** A status is a printed word with a coloured mark before it. The colour
never appears without the word, and the word never appears without its mark.

**The Pending Amber Rule.** Amber means not yet settled: a loading engine, an unsaved edit, an
unsure answer, an uncertain finding, a benchmark still under negotiation. It is never a highlight.

**The White Paper Rule.** Drawings and the Revit sheet sit on white in both themes, with their own
fixed inks; the theme changes the desk, not the paper.

## Typography

**Display Font:** IBM Plex Sans (with Helvetica Neue, Helvetica, Arial)
**Body Font:** IBM Plex Sans
**Label/Mono Font:** IBM Plex Mono (with SF Mono, Menlo, Consolas)

**Character:** A working sans that stays out of the way, set small and tight so a whole memo fits
the eye at once, and a mono that marks what the machine recorded. The loudest thing on the page
is a verdict sentence at 18px weight 600 with its operative words in the status text colour.

### Hierarchy
- **Title** (600, 18px, 1.3): the memo's title, the site address; the verdict sentence is the same
  size.
- **Wordmark** (600, 17px): the top bar's name with a muted 12.5px subtitle.
- **Heading** (600, 14px): panel and card headings, each with a 20px round badge in front.
- **Body** (400, 13px, 1.45): findings and prose; the first sentence of a finding is Ink, the rest Muted.
- **Small** (400, 12.5px): fields, selects, the status strip, captions, lists in the sections.
- **Label** (500, 12px, Muted): form labels above fields; help text at 11px.
- **Key** (600, 11px, 0.06em, uppercase): group labels, table headers, figure labels, title-block
  keys, the tour counter, pill text.
- **Table** (11.5px): the ledger's rows; 12px in the answer cards' tables.
- **Mono** (400, 11px): rule ids, numbers used, hashes, paths, the shell lines; the engine chip at
  11px 500 uppercase.
- **Stamp** (600, 11.5px mono, 0.08em, uppercase): the version stamp inside a double rule.

### Named Rules
**The Lead Sentence Rule.** In any finding, the first sentence is Ink and the continuation is Muted.
Hierarchy inside a paragraph comes from colour, not weight.

**The Key Rule.** Every small uppercase label is the same key: 11px, 600, 0.06em. It names a group,
a column, a figure or a title-block field, and nothing else.

**The Machine Mono Rule.** Mono is for text a machine produced or will consume: stamps, ids,
hashes, paths, shell lines, the as-of date. Human sentences are never set in mono.

## Layout

Two panes under a 46px top bar and a 38px step bar, both sticky, with the status strip beneath
them: the input rail on the left at min(420px, 36vw) on the page grey with a 1px line on its right,
the memo on the right taking the rest. The rail holds the Site and Option panels 12px apart with
16px side padding; the memo pane has 20px side padding. Below 1100px the panes stack and the two
input panels sit side by side; below 760px everything is one column and the bars stop sticking.
At 1600px and above the memo body becomes two columns, the answers and the rest on the left, the
figures in a 420px column on the right.

Rhythm is a 4px scale: 4, 6, 8, 12, 14, 16, 20. Panels carry 12px by 14px of padding and sit 12px
apart. Forms are a single column with 8px between fields and 6px within a group; groups are
separated by a 1px line with 10px above. Short numeric fields share a row with an 8px gap. The
memo's title block is a row of key-over-value cells separated by 1px lines under a 2px ink rule.

## Elevation & Depth

Nearly flat. Panels are a 1px line and a one-pixel shadow (`0 1px 2px rgba(20, 30, 40, .06)`) on
the page grey; the Export panel adds a 2px ink rule along its top. Buttons gain a small shadow on
hover and lose it on press. The walkthrough card floats over a dimmed page with a deep shadow
because it is genuinely above everything.

### Shadow Vocabulary
- **Panel** (`0 1px 2px rgba(20, 30, 40, .06)`): every card at rest; `.3` alpha black at night.
- **Button hover** (`0 2px 6px rgba(20, 30, 40, .25)`): the primary button while hovered.
- **Walkthrough card** (`0 10px 30px rgba(0, 0, 0, .28)`): the guided-tour card only.
- **Spotlight** (`0 0 0 9999px rgba(20, 30, 40, .45)` plus a 2px blue ring): the tour's cut-out.

### Named Rules
**The One Pixel Rule.** A panel's shadow is one pixel; it says "sheet on a desk", not "floating".
Only something that is actually above the page casts more.

## Shapes

Small and consistent: marks and the stamp box 2px, fields and small controls 4px, buttons 5px,
panels 6px, the tour card and spotlight 8px, pills 10px, badges and status marks fully round.
Borders are 1px Line everywhere; the three-state control is one 4px box whose chosen segment fills
Ink (Amber for "Not sure"). The uncertain pill alone has a dashed amber border. Figures are drawn
with 1px non-scaling strokes.

## Components

### Buttons
Dark and plain; they say what they do.
- **Shape:** 5px radius, 30px minimum height, 13px weight 500, 6px by 12px padding; small variant
  26px high at 12px.
- **Primary:** Ink fill, Panel text. One per screen: Run the rules; the walkthrough's Next and
  Take the walkthrough.
- **Secondary:** Group fill, Ink text; the action bar's downloads, Print, Check Revit result.
- **Quiet:** transparent with a Line border; Save as…, Copy, Back, Not now.
- **Hover:** primary mixes 24% Panel into Ink and casts the hover shadow; secondary deepens 18%
  toward Ink with a darker border. **Press:** translateY(1px), shadow off. Disabled sits at 45%
  opacity. On a coarse pointer every control is 44px tall.

### Status pills
- **Style:** a 14px round mark with a glyph (✓ ! ✗ ? – i) in the status colour, then the word in
  the status text colour at 11px 600, on the status wash, 10px radius, 2px by 8px.
- **State:** none; a pill is a printed word. Layer summaries show counts beside the word.

### Status strip
One line under the step bar, sticky: a 9px dot and a sentence at 12.5px on the Status Info wash.
`ok` turns it green, `error` red, `busy` amber with the dot spinning. Every action writes here;
there is no toast.

### Panels / Cards
- **Corner Style:** 6px.
- **Background:** Panel; an answer card takes the wash of its verdict's status; figures take Paper.
- **Shadow Strategy:** the one-pixel shadow.
- **Border:** 1px Line.
- **Internal Padding:** 12px by 14px; figures 10px by 12px.

### Inputs / Fields
- **Style:** 1px Line on Field, 4px radius, 5px by 8px, 12.5px text; labels 12px Muted above, help
  11px below.
- **Focus:** 2px Blue outline, 1px offset; caret Blue.
- **Three-state control:** Yes / No / Not sure in one bordered box; the chosen segment fills Ink
  with Panel text, except Not sure, which fills Amber, so the honest choice is visibly pending.
- **Checkbox groups and tree rows:** ink-accented native checkboxes; compact 12.5px rows.

### Navigation
- **Step bar:** four 12.5px labels with a 20px round badge; the current step sits on a Group tab
  with its badge filled Ink, completed steps keep the filled badge, the rest are Muted. Hover
  tints the tab and draws a 3px inset underline. A "Walkthrough" link in Blue ends the bar.
- **Top bar:** the wordmark and subtitle, then the as-of date in a mono field, the primary button,
  the engine chip, and the version stamp as a mono uppercase double-rule stamp with a Copy button.

### Title block
The memo's header: an 18px title over a row of cells, each a Key over a 12.5px value, separated by
1px lines, under a 2px Ink rule; the stamp cell carries the mono stamp and the engine version.

### Answer cards
The signature component. A badge-numbered 14px heading, the verdict at 18px 600 with the operative
words in the status text colour, then findings in lead-and-continuation prose or a pill-led list;
the third card holds a table of open items with a Who / what column in Muted. Wash and tone come
from one `data-verdict` attribute.

### Segmented control
Plan | 3D on FIG 01 (and the pattern for any two-or-three-way view switch): one 4px box with a
Line border, 11.5px weight 500 segments at 3px by 10px, the pressed segment filled Draw Ink with
white text, the rest Draw Muted on paper; hover tints a segment Group.

### Figures
A white-paper card with a key-style figure label in Draw Muted, an SVG drawn in metres with
non-scaling strokes and IBM Plex Sans labels, a swatch legend, and a 12px caption carrying the
numbers; a caveat under a figure is set in Draw Note. FIG 03 is the Revit sheet image.

### Engine chip
A fully round mono label at 11px that reads loading (amber, with a spinner), ready (green) or
error (red), in the matching colour on a Line border.

### Walkthrough
A spotlight cut from a dimmed page with a 2px blue ring, and a Panel card with a Key counter, a
14px heading, 12.5px text, Back / Next buttons and an "Esc to close" note.

## Do's and Don'ts

### Do:
- **Do** set everything in IBM Plex Sans at 13px with 11px uppercase keys, and keep mono for what a machine wrote.
- **Do** print every status as a word with its round mark in front, on its wash.
- **Do** fill buttons with Ink (secondary with Group), lift them on hover and sink them 1px on press.
- **Do** keep Blue for links, focus and the active step, and Amber for what is pending.
- **Do** keep panels at 6px radius, 12px by 14px padding, 1px Line and the one-pixel shadow, 12px apart.
- **Do** keep the drawings on white paper in both themes with Lotwise's drawing tones.

### Don't:
- **Don't** build a dashboard: no gauges, KPI tiles, sparklines, or icon-plus-heading cards as structure.
- **Don't** reach for a landing page's kit: no gradients, glass, hero numbers, floating shadows, marketing voice.
- **Don't** bring back a serif, a 16px body, or large display type; the memo reads at drafting density.
- **Don't** put a status colour on a button, a heading or a background that carries no status.
- **Don't** add a toast, a second accent, or a shadow deeper than one pixel on anything at rest.
- **Don't** use "N/A", a colour without its word, or a checkbox where "not sure" is a legitimate answer.
