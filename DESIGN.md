---
name: First Read
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
  street-text: "#63635F"
  bench-text: "#8F5A0E"
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
  band: "#E7EEF5"
  band-line: "#D3DCE6"
  band-group: "#DBE4EE"
  night-band: "#191F26"
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
  revision:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "12.5px"
    fontWeight: 600
    lineHeight: 1.25
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

# Design System: First Read

## Overview

**Creative North Star: "The Drafting Tool"**

The memo is produced by a tool, and the tool looks like one: the same language as Kai's Lotwise
massing app, which is the pinned precedent. One sans, IBM Plex Sans at 13px, does nearly all the
talking; IBM Plex Mono is reserved for what a machine wrote down, rule ids, fingerprints, paths
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

The home page in front of the tool speaks the same language. It is read rather than operated, so its
running prose sits at a reading size while everything else keeps the tool's density, and it is kept
quiet: headings, short paragraphs, one table and one sheet of white paper (a row of the memo) below a
capture of the memo itself; the stages and the steps sit on the page under hairlines, without boxes.
When something changes between two readings of the rules, it is marked the way a drawing marks a
revision.

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
- **Street Text** (`{colors.street-text}`) and **Bench Text** (`{colors.bench-text}`): words drawn in
  those families, the street names and the benchmark's label, dark enough for 4.5:1 on the paper;
  the lines themselves keep Street Grey and Amber.
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
- **Band** (`{colors.band}`): the home page only. Every other section sits on this slate, the page's
  own hue one shade deeper (oklch 0.945 0.012 252), run the window's width so the page reads as
  segments; inside a band, **Band Line** (`{colors.band-line}`) and **Band Group**
  (`{colors.band-group}`) stand in for Line and Group, and white paper keeps its own cool rules. At
  night the band is `{colors.night-band}`, between the night page and panel. A warm beige was tried
  first and dropped: at hue 86 it sat on Amber's own hue, so it read as pending and dulled the amber
  marks on it; on slate, amber stays the page's one warm note.
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
answers. Two options read under the same rules are compared without it: their difference is in the
numbers, not the rules. Nothing else uses the delta.

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
  11px 500 uppercase. Nothing on either page is set below 11px.
- **Reading** (400, 14px, 1.6, a measure of 52ch, about 68 characters of Plex Sans): the home page's running prose only: the
  lede, the section paragraphs, the three steps, the close's paragraph. Its headline is 22px 600 (20px on a phone)
  and its section headings 18px; its cards, figures and labels stay at the sizes above.
- **Revision** (600, 12.5px sans): the memo's revision on its site, R1, R2…, in a 1px Ink box in the top bar and
  in bold in the title block.
- **Drawing labels** (IBM Plex Sans, 11.5px on screen): the figures are drawn in metres and scale
  with their card, so their labels are refitted to 11.5px whatever the card's width; context labels
  run at 0.9 of that, tree ids at 0.85, and labels over the half tone carry a thin paper halo.

### Named Rules
**The Lead Sentence Rule.** In any finding, the first sentence is Ink and the continuation is Muted.
Hierarchy inside a paragraph comes from colour, not weight.

**The Key Rule.** Every small uppercase label is the same key: 11px, 600, 0.06em. It names a group,
a column, a figure or a title-block field, and nothing else. It never sits above a heading as a
kicker: a heading speaks for itself.

**The Machine Mono Rule.** Mono is for text a machine produced or will consume: fingerprints, ids,
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
line up with that column at any width, and its four anchors mark the section the reader is in. On a
phone the bar stops sticking and the anchors take a second row. The first viewport is the headline,
lede and two ways in (the primary button and a plain link, the engine's download noted under them)
beside a capture of the memo itself, with the memo's three findings set in type under the picture,
in the memo's own pills. Then four sections, each 56px top and bottom (44px on a phone), each a
heading and a short paragraph at the reading size: the problem (five stages on a hairline, then the
rule layers as a table), how it works (three steps), one row of the memo on white paper, and the real
case with its three ways in (one button, two links). The sections alternate between the page grey and
a slate Band across the window's width (the problem and the memo row sit on the band), so each
reads as its own segment; the footer follows under a hairline. The steps sit three across down to
860px and stack below it; the stages run down the page below 640px.

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

Small and consistent: marks 2px, the revision box 3px, fields and small controls 4px, buttons 5px,
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
  Take the walkthrough; on the home page, the two "Run the real case with a walkthrough" buttons,
  each with its alternatives as plain links beside it.
- **Secondary:** Group fill, Ink text; Download memo (HTML), Print, Check Revit result, and the home
  page's top-bar Open the tool, so the hero's button is the page's one dark one.
- **Quiet:** transparent with a Line border; Save as…, Edit / Done, Copy, Back, Not now, the other
  downloads, Export to Revit, Hide inputs, Open all layers.
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
  the engine chip, and the memo's revision: a "Revision" key and R1, R2… in a small 1px Ink box.
  A skip link to the memo comes first in the tab order.

### Title block
The memo's header: an 18px title over a row of cells, each a Key over a 12.5px value, keys aligned
to the top, separated by 1px lines, under a 2px Ink rule; the Revision cell carries R1, R2… in bold
and the engine version. A comparison adds a cell: Revised from (the delta, the earlier memo's
revision and its rules date) when the rules moved, Compared with (the other memo's revision, its
option's name and date) when two options were read under the same rules.

### Revision
Every memo on a site is numbered as a revision, R1, R2 and so on, the way a drawing numbers its
issues, so two memos compared always carry two numbers. The committed runs come first: the base runs,
then the runs recorded against another (they carry a diff), each group by as-of date and folder; then
the runs made in the tool in the order they were made, so a new run always takes the next number. On
998 E 19th Ave the as-approved memo, which falls short, is R1, the funder-ready what-if that clears
every question R2, and the as-approved option under the 27 Oct rules R3; on 1010 Expo Blvd the
as-permitted memo is R1 and the 12-storey what-if R2. The top bar, the title block, the comparison,
the run pickers (each label leads with it), the status strip and the print footer say the R-number. The
rules stamp behind a memo (a hash of the rule files and the versions in force on its as-of date) is
never in the reading path: it appears once, as the fingerprint in the Rules fingerprint card at the
foot of the memo, and in the Revit elements' Comments. The downloadable memo files are written by the
engine and still print the stamp.

### Side by side
A comparison opens with it, directly under the title block.
- **Pickers:** the two run pickers ("Open a past run" and "Compare with…", above the memo otherwise)
  move into a row laid on its A and B columns, their keys renamed "A · This run" and "B · Compared";
  a hidden phrase keeps what each does in its accessible name. A picker that had focus keeps it as
  the memo is redrawn, wherever the picker lands. On a phone the two stack across the card. In print
  and when presenting the pickers hide and each option's name stands in their place.
- **Lead:** one sentence naming each side by its revision ("A, R2, against B, R1"): for two options,
  what they trade (units, storeys, height, floor area) and the shared rules date; for two readings of
  the rules, each revision's rules date.
- **Answers:** the four answers for each run as pills, open items included; under them, behind a
  disclosure, each run's open items with the person who resolves them.
- **Rules:** "n of 14 rules read differently" over a table of only those rules, each status with
  what that option proposed under it; the rules that read the same wait behind a disclosure. No row
  band and no ≠: the table holds only differences.
- The answer cards below carry no A | B strip; this card is the comparison's one place.
- Choosing the same run for A and B clears the comparison, and the status strip says why. A run
  recorded against an earlier one opens compared with it, when the run list can tell which run that
  was (same date, rules stamp and option); otherwise the note beside the pickers says what it was recorded
  against.

### What changed
Under the Side by side card. When the rules moved: a 14px heading with the delta, the two revisions (R1 → R3) and
why they differ (the rule files, the as-of date, the site's or the option's inputs, read from the two
ledgers), "Same verdict, new version" when only the version moved, and a table of Rule, Version in
force (old struck through, then new), Status and Now reads; changed rows in the clauses and the
ledger carry the delta and their layer opens. Between two options: "What changed between the two
options", "R1 → R2 · same rules, as of …", no version column, the status read B → A, and "numbers changed"
where the engine says a finding was reworded. Rows are named by the rule's title over its id. On a
phone the table stacks, each value under its column's name.

### Answer cards
The signature component. A badge-numbered 14px heading, the verdict at 18px 600 with the operative
words in the status text colour, then findings in lead-and-continuation prose or a pill-led list;
the third card holds a table of open items with a Who / what column in Muted. Wash and tone come
from one `data-verdict` attribute.

### Segmented control
Plan | 3D on FIG 01 (the pattern for any two-or-three-way view switch): one 4px box with a Line border, 11.5px weight 500
segments at 3px by 10px, the pressed segment filled Draw Ink with white text, the rest Draw Muted
on paper; hover tints a segment.

### Figures
A white-paper card with a key-style figure label in Draw Muted, an SVG drawn in metres with
non-scaling strokes and IBM Plex Sans labels at a fixed 11.5px, a swatch legend, and a 12px caption
carrying the numbers; a caveat under a figure is set in Draw Note. A drawing is at most 440px tall
on screen. The plan and the section draw the outright mass as a heavy dashed outline over the
proposed fill (and the legend's swatch says so); the plan adds dimension strings with ticks along
the frontage and the depth, a scale bar in two halves, a north arrow only where the site's
OpenStreetMap frame gives the bearing, and always names the address street, beside the lot, its
street names in Street Text. The section's height labels (benchmark in Bench Text, proposed, outright)
sit at their heights and are pushed apart where two would overprint, a thin leader joining a moved
label to its line; its note under the ground line starts at the lot's edge. The axonometric leads its
height labels off the masses on leader lines, turns under a sideways drag (vertical swipes still
scroll a phone) and under the arrow keys. FIG 03 is the Revit sheet image.

### Home page devices
HTML, never pictures of it, so everything reflows and keeps the page's type sizes. Only the memo row
sits on paper; the rest sits on the page.
- **Stages:** five on one Line hairline, each a 9px dot over its name and, where it has one, a 12px
  Muted note; the memo's stage has the filled Ink dot and the note "the memo reads layers A to E",
  tying it to the table's layer keys. Below 640px they run down a vertical hairline.
- **Rule layers:** a table on the page (layer key, what it covers; who usually reads it; when) with
  Key column heads and 1px Line rows. On a phone it stacks, each value after its column's name.
- **Steps:** three columns, each under a 1px Line rule, a badge-numbered 14px heading over a
  paragraph at the reading size; the third lists the memo's three questions, each in Ink with its
  qualifier in Muted, then a 13px Muted sentence on the massing and the Revit sheet.
- **Findings under the hero:** the as-approved memo's three answers as a small definition list,
  each question a 12.5px key beside its answer in the memo's pills; one column on a narrow phone.
- **One row of the memo:** white paper (1px Line, 6px corners, the one-pixel shadow, 16px by 18px of
  padding) holding the row's five columns, each a Key over a 1px Line and its value; when narrow each
  column becomes a key beside its value. A "Who resolves it" band follows on the conditional wash.

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
switches, and a footer on every page with the address, the as-of date, the memo's revision and the page
number. The home page prints light, its memo row and steps unbroken, with the tool's address in place
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
- **Do** number a site's memos as revisions, R1, R2…, and keep the rules stamp's hash to the Rules fingerprint card.
- **Do** alternate the home page's sections between the page grey and the slate Band, edge to edge.
- **Do** reach for the drawing set's own devices (title block, schedule, general notes, an issued sheet) before a generic card.
- **Do** draw explanatory figures in HTML, not SVG text, so they reflow on a phone and read at the page's own sizes.

### Don't:
- **Don't** build a dashboard: no gauges, KPI tiles, sparklines, or icon-plus-heading cards as structure.
- **Don't** reach for a landing page's kit: no gradients, glass, hero numbers, floating shadows, marketing voice.
- **Don't** bring back a serif, a 16px body, or large display type; the memo reads at drafting density, and the home page's prose stops at 14px.
- **Don't** box what can sit on the page: the home page keeps one sheet of paper below the hero, one primary button per action group, and lets hairlines and space do the rest.
- **Don't** put a status colour on a button, a heading or a background that carries no status.
- **Don't** add a toast, a second accent, or a shadow deeper than one pixel on anything at rest.
- **Don't** use "N/A", a colour without its word, or a checkbox where "not sure" is a legitimate answer.
- **Don't** set amber as text on white, put a key above a heading as a kicker, or end a page on a dark band of buttons.
