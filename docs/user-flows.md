# User flows: First Read

Written 2 Nov 2026 for the redesign of the site and the tool. Three readers, one memo. Each flow names
the screen it lands on, so the site and the tool are laid out around what each person actually does.
The engine is untouched; the flows only decide what is shown first, what is one click away, and what
can wait behind a disclosure.

## The readers

| Reader | Comes with | Wants | Leaves with |
|---|---|---|---|
| Development manager at a non-profit | an address, a rough option, a board meeting date | the three answers and who resolves each open item | the PDF memo for the board; a list of people to call |
| Architect doing the feasibility work | the option's numbers, a Revit seat | the ledger's arithmetic and clauses, the massing, a comparison of two options | an option file, two memos compared, masses on an annotated Revit sheet |
| Board member, planner or funder's officer | the PDF, no briefing | two pages they can follow and cite | a vote, a comment on an uncertain rule, a read of the funding fit |

## Flow 1: the development manager (site in, memo out)

```
site (home) ──► the case ──► tool: memo on screen (R1)
                                   │
   "Working on a site of your own?" │
                                   ▼
                 tool: Site card ─► Option card ─► Run the rules ─► three answers
                     (not sure is a normal answer)                       │
                                                                          ▼
                                                   open items, each with a named person
                                                                          │
                                                                          ▼
                                                    Export: Download PDF ─► the board
```

1. **Home.** Reads the three questions and one real finding. One click: *Run the real case*.
2. **The tool opens on the memo, not on a form.** The real case is loaded; the answers are on screen
   before anything is typed. The inputs rail sits beside the memo and folds away.
3. **Start from an address** (built 3 Nov 2026, the guided card at the top of the rail, seven stops):
   1. *Find the site*: an address; the City's address list gives the point, its open data the zoning
      district and the parcel, which becomes the lot's area and an equivalent rectangle. Or a saved site.
      With a key on the local machine, *Ask Claude about this site*: the model proposes the odd lot's
      rectangle, its frontage street and what is odd, with evidence and a confidence; the manager confirms
      each field by name, and the site file records it.
   2. *Choose the programs*: the funders in view.
   3. *Read the site*: layers A to C on the site alone, shown in the memo pane before any option.
   4. *Shape the option*: Outright, Benchmark or Funder-ready, derived from the rules; every figure
      Suggested | Mine with its rule beside it; what no rule settles (Community Vision area, transit
      area, tenure, developer partner, site control) answered right there.
   5. *Run the rules*: under a second; the three answers land in order, then a fourth: does the money
      work (capital cost, net operating income, the funding stack, the gap; likely / unlikely / unsure).
   6. *Pro-forma*: the five lines from the run; land, equity and other grants are the manager's; *Run
      again with these*. Every line cites its assumption (layer F) or program (layer E).
   7. *Issue*: a note, and the architect sees the revision in their top bar.
4. **Three views** of the result: Summary (title block, answers, figures), Detailed (the whole memo),
   3D preview (the site plan with dimensions, the section, the axonometric, large).
5. **Open items.** The third answer is a table: item, status, who resolves it. This is the to-do list.
6. **Export.** *Download PDF* is the one button that matters here; everything else is quieter.

Design consequences: the tool's first screen is a memo; *Run the rules* is the only loud button;
the open-items table names a person in its own column; the PDF button leads the Export bar.

## Flow 2: the architect (option in, comparison and massing out)

```
tool: memo R1 ─► Option: Edit ─► change storeys / units / setbacks ─► Run ─► memo R2
                                                                            │
                                   Compare with… R1 ◄───────────────────────┘
                                          │
                                          ▼
                     Side by side: the trade-off, only the rules that differ
                                          │
                                          ▼
                 FIG 01 plan | 3D · FIG 02 section ─► Export to Revit ─► Check Revit result ─► FIG 03 sheet
```

1. **Opens a run** (a past run from the picker, or a link from the site with `?run=`).
2. **Edits the option.** Fields carry marks: needed to run, read by a rule, drawings only. *Save
   option as…* writes a new file so the run is reproducible from the command line.
3. **Runs again.** The new memo is the next revision on that site (R2).
4. **Compares.** *Compare with…* R1. The Side by side card sits under the title block: one sentence
   on what the two options trade, the four answers for each, only the rules that read differently.
5. **Reads the ledger.** Layer by layer, each row with its numbers used and its source link.
6. **Takes the massing to Revit.** Export panel: the massing.json path, two shell lines, then
   *Check Revit result* brings the sheet back as FIG 03.

Design consequences: the input cards collapse to a summary line and open on Edit, so the memo keeps
its width; revisions are numbered R1, R2… everywhere a run is named; the figures sit beside the
answers on a wide screen; the Export panel is instructions plus a result check, never a launcher.

## Flow 3: the board, the planner, the funder's officer (PDF in, decision out)

```
PDF page 1: title block · three answers with the rules that decide them
PDF page 2: open items · who resolves each · the comparison, if any
pages 3+:   clauses applied · massing · full ledger · inputs · sources · how to reproduce
```

1. **Reads page one cold.** The address, the option, the revision and the rules date, then the three
   answers. No dashboard, no colour without a word.
2. **Reads page two.** The open items, each with a person. A planner looks for the uncertain rules;
   a funder's officer for the funding-fit answer and the missing figures.
3. **Follows a reference.** Every rule is A1 to E4; every source has a number and a URL.
4. **Decides.** The board votes the pre-development money or not. The memo is dated, so a later
   reader can tell whether it is still true.

Design consequences: the site's "The case" page is laid out like page one of the PDF; status is a
word with a mark; the revision and the rules date are in every title block.

## The process the memo sits in

Five stages, from the research document: Site found → Feasibility → Pre-development ($200k to
$500k) → Funding bid → Decision. Today the first reliable answer arrives at the end; with the memo it
arrives at stage two, in hours, dated and cited. Each rule layer is read today by a different person
at a later stage (A: City planning staff at pre-application; B and D: the architect during design;
C: planners and an arborist once a site plan exists; E: the development manager when a call opens).
The memo reads all five on day one.

## The switch in the tool

The three flows are three layouts of the same page, chosen with Manager · Architect · Reader in the
tool's top bar (`?mode=manager|architect|reader` in a link; kept in the browser for the next visit):

| Mode | Inputs rail | Forms | Ledger | Run controls | Export bar leads with |
|---|---|---|---|---|---|
| Manager | open, cards as summaries | on Edit | closed | yes | Download PDF |
| Architect | open, forms open | open | every layer open | yes, with the pickers | Export to Revit, massing.json |
| Reader | hidden | hidden | closed | none | Download PDF, Print |

The engine, the memo and its numbers are the same in every mode.

## Site map

| Page | Who it is for | What it holds |
|---|---|---|
| `index.html` (home) | everyone, first visit | the three questions; the real case's answers; the gate diagram; three steps; three readers; one call to action |
| `how.html` | the architect, the reviewer | inputs → rule stack → outputs; the tool logic (script, model, check, person); the five layers; the four steps of the tool |
| `who.html` | the development manager, the board | who reads which layer, and when; the three flows above, step by step; what stays with people |
| `case.html` | the board, the funder's reader | 998 E 19th Ave as page one of the memo: title block, three answers, open items, revisions; 1010 Expo Blvd |
| `brand.html` | whoever builds on this | the mark, the wordmark, colour, type, voice, components, diagram style |
| `app.html` | the manager and the architect | the tool |
