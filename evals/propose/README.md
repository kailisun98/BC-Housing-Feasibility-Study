# Evaluation set for the proposal step

Each folder is one case: a `document.txt`, `.pdf` or image the model reads, and an `expected.json` with the
values a person worked out by hand. `python -m ffm propose eval` (with `FFM_CLAUDE_KEY` set) runs every case
and scores it field by field; a number counts when it is within 1% of the expected figure, a string when it
matches ignoring case and spacing. A change to the prompt, the tool schema or the model is accepted only when
the score does not fall.

| Case | What it tests |
|---|---|
| `rule-rt9-synthetic` | A hand-written district schedule (RT-9 is not a real district): the base FSR and height go in the maximums, the Director's conditional increases stay out of them; yards; coverage; the consolidation date. |

Real schedules are not kept here: the City's by-law site refuses automated downloads, so a person saves the
PDF locally and runs `python -m ffm propose rule --from <the pdf> --district RT-3 --url <its address>`; the
proposal file in `proposals/` carries the document's name and hash, never its bytes.
