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
  amber-ink: "#14181D"
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
  half-road: "#E9E9E6"
  half-parcel: "#F4F4F2"
  half-building: "#E2E2DF"
  half-line: "#C9C9C5"
  tree: "#9FB07F"
  tree-line: "#7F9664"
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
  three-state-not-sure:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.amber-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    padding: "5px 8px"
  drawing-sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.draw-ink}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
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

The home page in front of the tool speaks the same language at the same density, and borrows the
drawing set's own devices where it needs structure: a week ruler on a sheet with a title block, a
schedule with numbered general notes, and a sheet issued for review to close on. When something
changes between two readings of the rules, it is marked the way a drawing marks a revision.

**Key Characteristics:**
- One sans at 13px with 11px uppercase keys; mono only for machine-written text.
- Slate ink, cool grey page, white panels; dark mode is the same tool at night, not an inversion.
- Buttons are ink-filled; the secondary ones take the group grey. Hover lifts, press sinks 1px.
- A status is a word on a tinted pill with a round mark and a glyph before it.
- Numbered badges stand in for section numbers; step panels and answer cards share them.
- Drawings are always on white paper, whatever the theme.
- A comparison is a revision: a delta with its letter beside whatever changed.

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
  the engine chip's border while loading, the uncertain status mark, the staff benchmark line in
  the section. Anything set on an amber fill takes **Amber Ink** (`{colors.amber-ink}`, 5.4:1);
  amber words on a light ground take **Uncertain Text** (`{colors.uncertain-text}`): the
  dirty-form note, the loading chip's text, a field warning.
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
  labels, dimension strings, the scale bar, the north arrow and captions; **Draw Note**
  (`{colors.draw-note}`): a caveat under a figure.
- The setback envelope is a red dashed line; the staff benchmark an amber one. Both keep their
  light values on the legend as well as in the drawing, in either theme.
- The context around the lot is drawn in **half tone**: roads **Half Road** (`{colors.half-road}`),
  parcels **Half Parcel** (`{colors.half-parcel}`), neighbouring buildings **Half Building**
  (`{colors.half-building}`) with **Half Line** (`{colors.half-line}`) outlines, trees **Tree**
  (`{colors.tree}`) with **Tree Line** (`{colors.tree-line}`). The figures read every drawing colour
  from the stylesheet's `--c-*` tokens; none is written into the script.

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
unsure answer, an uncertain finding, a benchmark still under negotiation. It is never a highlight,
and never text on white: amber itself is 3.3:1, so words take Uncertain Text and fills take Amber Ink.

**The White Paper Rule.** Drawings and the Revit sheet sit on white in both themes, with their own
fixed inks; the theme changes the desk, not the paper. A light-token reset on paper re-declares the
derived tokens too (the status marks are resolved where they are defined, so they would keep the
night colours otherwise).

**The Revision Rule.** When two readings of the rules are compared, what changed carries a delta
with its letter (A) and the comparison's answer sits right under the title block, before the three
answers. Nothing else uses the delta.

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
  11px 500 uppercase; the home page's week numbers at 12px 500 in Draw Ink.
- **Stamp** (600, 11.5px mono, 0.08em, uppercase): the version stamp inside a double rule.
- **Drawing labels** (IBM Plex Sans, 11.5px on screen): the figures are drawn in metres and scale
  with their card, so their labels are refitted to 11.5px whatever the card's width; context labels
  run at 0.9 of that, tree ids at 0.85, and labels over the half tone carry a thin paper halo.

### Named Rules
**The Lead Sentence Rule.** In any finding, the first sentence is Ink and the continuation is Muted.
Hierarchy inside a paragraph comes from colour, not weight.

**The Key Rule.** Every small uppercase label is the same key: 11px, 600, 0.06em. It names a group,
a column, a figure or a title-block field, and nothing else. It never sits above a heading as a
kicker: a heading speaks for itself.

**The Machine Mono Rule.** Mono is for text a machine produced or will consume: stamps, ids,
hashes, paths, shell lines, the as-of date. Human sentences are never set in mono.

## Layout

Two panes under the bars: a top bar of at least 46px, the step bar and the status strip stick
together as one block, and the top bar grows a row rather than let its controls overflow. The
input rail sits on the left at min(420px, 36vw) on the page grey with a 1px line on its right, the
memo on the right taking the rest. The rail holds the Site and Option cards 12px apart with 16px
side padding; once a file is chosen each card collapses to its file and a one-line summary, and
Edit opens the form. "Hide inputs", in the step bar beside Walkthrough, sets the rail aside, with the
run tools and the walkthrough offer, so the memo takes the width, for presenting.
The memo pane has 20px side padding, and anything a link or a step lands on keeps a scroll margin
the height of the bars. Below 1100px the panes stack and the two input cards sit side by side;
below 760px everything is one column and the bars stop sticking. At 1600px and above the answers
and the figures sit side by side, the figures in a 460px column, and the ledger and the rest run
the full width beneath.

The home page is one 1280px column with a 20px gutter (16px on a phone); its top bar's contents
line up with that column at any width. Sections sit 36px apart, each a heading, a paragraph and
then its material: the ruler sheet in the first viewport, the rule-layer schedule, the three
answers beside a ledger row and a section, the rule change, the limits, and the issued sheet.

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
with 1px non-scaling strokes. The revision delta is a 16 by 14 outlined triangle with its letter,
and a revision cloud is a 1px dashed ink outline at a 7px radius around the words that changed.

## Components

### Buttons
Dark and plain; they say what they do.
- **Shape:** 5px radius, 30px minimum height, 13px weight 500, 6px by 12px padding; small variant
  26px high at 12px.
- **Primary:** Ink fill, Panel text. One per screen: Run the rules; the walkthrough's Next and
  Take the walkthrough; on the home page, Open the tool and the issued sheet's Run the case.
- **Secondary:** Group fill, Ink text; Download memo (HTML), Print, Check Revit result.
- **Quiet:** transparent with a Line border; Save as…, Edit / Done, Copy, Back, Not now, the other
  downloads, Export to Revit, Hide inputs, Open all layers, the home page's Watch a rule change and
  Read the memo.
- **Hover:** primary mixes 24% Panel into Ink and casts the hover shadow; secondary deepens 18%
  toward Ink with a darker border. **Press:** translateY(1px), shadow off. Disabled sits at 45%
  opacity; a disabled download link has no href, so it is out of the tab order too. On a coarse
  pointer every control is 44px tall. The base style is the single class `.btn`, so the variants
  and the touch rule can override it.

### Status pills
- **Style:** a 14px round mark with a glyph (✓ ! ✗ ? – i) in the status colour, then the word in
  the status text colour at 11px 600, on the status wash, 10px radius, 2px by 8px.
- **State:** none; a pill is a printed word. Layer summaries show counts beside the word.

### Status strip
One line under the step bar, sticky with it: a 9px dot and a sentence at 12.5px on the Status Info
wash. `ok` turns it green, `error` red, `busy` amber with the dot spinning. Every action writes
here, including opening a past run, a comparison and reading the Revit result; there is no toast.

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
  with Panel text, except Not sure, which fills Amber with Amber Ink, so the honest choice is
  visibly pending. It is a radio group: one tab stop on the chosen answer, arrows move the choice.
- **A blank number** reads as "not sure" to the engine, and its empty field says so in an italic
  placeholder. A share written as a percentage (30 for 30%) gets a field warning in Uncertain Text.
- **Checkbox groups and tree rows:** ink-accented native checkboxes; compact 12.5px rows; each
  tree row's remove button is named for its tree.
- **Input cards:** collapsed, a card shows its file select and a summary line (address, district,
  area and dimensions, and how many answers are "not sure"; or the option's storeys, height, floor
  area, units and tenure), with Edit to open the form and Done to close it.

### Navigation
- **Step bar:** four 12.5px labels with a 20px round badge; the current step (`aria-current`)
  sits on a Group tab with its badge filled Ink, a step whose work is done (a site, an option, a
  memo on screen) keeps the filled badge, the rest are Muted. The current step follows where the
  reader works: focus or a click in a panel, and scrolling in the memo pane. A step link moves focus
  to its panel. Hover tints the tab and draws a 3px inset underline. A "Walkthrough" link in Blue
  ends the bar.
- **Top bar:** the wordmark (a link back to the home page) and subtitle, then the as-of date in a
  mono field (the date of the memo on screen, and of the next run), the primary button (Ctrl+Enter),
  the engine chip, and the version stamp as a mono uppercase double-rule stamp with a Copy button.
  A skip link to the memo comes first in the tab order.

### Title block
The memo's header: an 18px title over a row of cells, each a Key over a 12.5px value, keys aligned
to the top, separated by 1px lines, under a 2px Ink rule; the stamp cell carries the mono stamp and
the engine version. A comparison adds a Revision cell: the delta, the earlier date and its stamp.

### What changed
A comparison's answer, directly under the title block: a 14px heading with the delta, the two
stamps and why they differ (the rule files, the as-of date, the site's or the option's inputs, read
from the two ledgers), "Same verdict, new version" when only the version moved, and a table of Rule, Version in
force (old struck through, then new), Status and Now reads. Changed rows in the ledger carry the
delta and their layer opens. On a phone the table stacks, each value under its column's name.

### Answer cards
The signature component. A badge-numbered 14px heading, the verdict at 18px 600 with the operative
words in the status text colour, then findings in lead-and-continuation prose or a pill-led list;
the third card holds a table of open items with a Who / what column in Muted. Wash and tone come
from one `data-verdict` attribute.

### Segmented control
Plan | 3D on FIG 01, and on the home page Without / With the memo and Rules as of 23 / 27 Oct (the
pattern for any two-or-three-way view switch): one 4px box with a Line border, 11.5px weight 500
segments at 3px by 10px, the pressed segment filled Draw Ink with white text, the rest Draw Muted
on paper; hover tints a segment.

### Figures
A white-paper card with a key-style figure label in Draw Muted, an SVG drawn in metres with
non-scaling strokes and IBM Plex Sans labels at a fixed 11.5px, a swatch legend, and a 12px caption
carrying the numbers; a caveat under a figure is set in Draw Note. A drawing is at most 440px tall
on screen. The plan and the section draw the outright mass as a heavy dashed outline over the
proposed fill (and the legend's swatch says so); the plan adds dimension strings with ticks along
the frontage and the depth, a scale bar in two halves, a north arrow only where the site's
OpenStreetMap frame gives the bearing, and always names the address street, beside the lot. The axonometric leads its
height labels off the masses on leader lines, turns under a sideways drag (vertical swipes still
scroll a phone) and under the arrow keys. FIG 03 is the Revit sheet image.

### Drawing sheets (home page)
White paper, 1px Line, 6px corners, the one-pixel shadow, with the drawing devices the page's
argument needs:
- **The ruler sheet:** a segmented switch and caption, the WK 0 to WK 12 ruler, a design band whose
  redraws are hatched (the drafting convention for work done twice), six findings hung from their
  weeks by leaders in two lanes, and a title block of Site, Option, Rules as of, Timing and Stamp.
  The switch moves the findings to a day-one grid where they gain their pill and their "Who"
  (FLIP, 420ms ease-out; instant under reduced motion). On a phone the weeks run down the page, the
  band stays in short labels and the switch sticks under the top bar. Print shows the day-one grid.
- **The schedule:** the rule layers as a table with an ink-keyed layer letter, then numbered
  general notes under a Notes key, then a schedule label in the figure-block style.
- **The issued sheet:** the page's close. A heading and paragraph, the three actions as title-block
  cells (Run, Compare, Read) each with its button and a sentence, and a title block of Issue (For
  review), Site, Rules as of and the stamp of the memo the Read action opens.

### Engine chip
A fully round mono label at 11px that reads loading (amber, with a spinner), ready (green) or
error (red), in the matching colour on a Line border.

### Walkthrough
A spotlight cut from a dimmed page with a 2px blue ring, and a Panel card: a modal dialog named by
its 14px heading, 12.5px text, Back / Next buttons and a Key counter ("3 of 9 · Esc closes"). Tab
stays inside the card, the arrows page through it except inside a field or the 3D view, and Esc
returns focus to where it was.

### Print
The memo prints alone, light whatever the theme, every ledger layer open, the figures without their
switches, and a footer on every page with the address, the as-of date, the stamp and the page
number. The home page prints its argument in the day-one state, with the tool's address in place
of the buttons.

## Do's and Don'ts

### Do:
- **Do** set everything in IBM Plex Sans at 13px with 11px uppercase keys, and keep mono for what a machine wrote.
- **Do** print every status as a word with its round mark in front, on its wash.
- **Do** fill buttons with Ink (secondary with Group), lift them on hover and sink them 1px on press.
- **Do** keep Blue for links, focus and the active step, and Amber for what is pending.
- **Do** keep panels at 6px radius, 12px by 14px padding, 1px Line and the one-pixel shadow, 12px apart.
- **Do** keep the drawings on white paper in both themes with Lotwise's drawing tones.
- **Do** mark a comparison as a drawing revision: a delta A beside each change, the answer under the title block.
- **Do** reach for the drawing set's own devices (title block, schedule, general notes, an issued sheet) before a generic card.

### Don't:
- **Don't** build a dashboard: no gauges, KPI tiles, sparklines, or icon-plus-heading cards as structure.
- **Don't** reach for a landing page's kit: no gradients, glass, hero numbers, floating shadows, marketing voice.
- **Don't** bring back a serif, a 16px body, or large display type; the memo reads at drafting density.
- **Don't** put a status colour on a button, a heading or a background that carries no status.
- **Don't** add a toast, a second accent, or a shadow deeper than one pixel on anything at rest.
- **Don't** use "N/A", a colour without its word, or a checkbox where "not sure" is a legitimate answer.
- **Don't** set amber as text on white, put a key above a heading as a kicker, or end a page on a dark band of buttons.
