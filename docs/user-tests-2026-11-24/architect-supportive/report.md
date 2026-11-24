# First Read, reviewed from a supportive-housing practice (AI role-play, 24 Nov 2026)

*A simulated review by an AI playing an architect whose work is mostly supportive housing, shelters, women's
transition housing and Indigenous-led housing. Not a practitioner's statement; never to be quoted as one. The
reviewer's files were kept in a scratch folder outside the repository.*

## 1. Sites, programs and results

**Lookups.** Three of the first eight addresses were refused (425 Princess, 2610 Kingsway, 4410 Kaslo), each with a
"nearest parcel" well away from the lot typed: 2610 Kingsway resolved to 488 Kingsway, 2221 Main to 1618 Quebec St (a
CD-1 lot). The refusal is right. The problem for this seat: City-owned vacant lots and church lands often have no civic
address in the City's list, and there is no way in by PID, by clicking a parcel, or by drawing a lot.

**A. 525 Powell St** (DEOD, 1,983 m², corner of Powell and Jackson). 40 supportive studios with a 24/7 desk, staff
office, a 250 m² clinic and amenity at grade; `supportive`, 500 m² non-residential, 5 storeys, a 4.5 m ground floor,
development permit, operator named, staffing $1.1M a year, a $1.3M subsidy sought. Outright yes with conditions (FSR
1.21 against 1.0, the Director's increase under s.6.5.4); by rezoning not needed; funders not assessed (4 programs
listed); money "needs more sources", 100% gap. 23 of 40 studios placed.

**B. 488 Kingsway** (C-2A, 2,873 m², irregular corner lot). A 60-bed shelter: `shelter`, `beds: 60`, no units, 3
storeys, 1,500 m², staffing $2.4M a year, a $2.9M subsidy sought. Outright yes; funders not assessed; money "Unsure: the
option has no homes entered"; layout "0 of 0 units". Re-run with the beds typed as 15 "studios" to get any operating
figures at all.

**C. 1130 Jervis St** (RM-5B, 803.6 m², a church corner lot). Second-stage housing for women and children leaving
violence over a kept hall: 24 homes, `transitional`, `women_leaving_violence: true`, 2,200 m² (FSR 2.74), 6 storeys at
18.3 m. **Outright no**, "rezoning is required (none)", while answer 1b says "By rezoning: not needed". Exits fail on all
6 floors; 15 of 24 homes placed. With the front set to Jervis St the verdict flipped (defect 2).

## 2. The workflow against the tool

| Step | Tool | Verdict |
|---|---|---|
| 1. Pin the site, often a City or church lot with no address | Address lookup only | Partly: unaddressed lots cannot be entered. |
| 2. Envelope and approval route (DP under an ODP vs rezoning) | Layer A, `approval_route`, DEOD sub-areas, RM-5 discretion | Partly: Powell reads well, Jervis wrongly. Whether the use (shelter, clinic) is permitted is never asked. |
| 3. The operator's program brief: rooms or beds, 24/7 desk, staff, clinic, meals, laundry, harm reduction | One `non_residential_gfa_m2` figure; amenity at 1.5 m² a unit | Missing. |
| 4. Unit and bed standards (BC Housing 2019, Shelter, women's transition guidelines) | Unit areas and 4.6 m² a bed read; the transition guidelines not read into the rules | Partly. |
| 5. Test-fit and plates | Solver and block editor | Partly: plate from GFA ÷ storeys, no podium, no beds placed. |
| 6. Funder door: SHF, WTHF, ESP, Reaching Home | Listed, not tested; who to ask named | Covered honestly, but answer 4 contradicts it. |
| 7. Operating budget with the operator | The operating page | Partly: works for supportive housing, breaks for a shelter. |
| 8. Pre-application to the City, then the funder | Open items with "Ask:" | Partly: nowhere to record what staff said. |
| 9. Confidentiality of a transition house address | Nothing | Missing. |

## 3. What is not working, ranked

### Real defects

1. **The shelter's operating page throws away what the operator entered.** `proforma.json`: `support_staffing: null`,
   `subsidy: null` despite $2,400,000 and $2,900,000 entered; the table reads "Support staffing | not given | none
   entered"; the verdict reason is "the option has no homes entered" and the item left to a person is "the unit mix".
   Typing the bed rooms as studios gives "$13,925 a home a month" beside "A funder compares the subsidy a home a month";
   for a shelter the funder compares per bed.
2. **The front street the tool picks flips the outright answer at Jervis.** The lookup turned the corner lot so the
   20.1 m Pendrell side is its width; `fsr_limit` then applied RM-5B's narrow-site cap (at most 2.0 under 20.2 m), never
   named in the finding: "FSR 2.74 exceeds the outright maximum of 1.0 … rezoning is required (none)". With the front set
   to Jervis: "yes, with conditions … at most 2.75". The rerun also printed "massing skipped: No road named 'Jervis St'
   adjoins the lot", against the lookup's own "the address faces Jervis St along the lot's 39.9 m side".
3. **Answer 1 and answer 1b contradict each other, and the input leaks into the finding**: "rezoning is required (none)"
   (from `rezoning_path: "none"`) beside "By rezoning: not needed … approved by a development permit". The fail branch
   tests `if path:` and not `approval_route`.
4. **The money answer contradicts the funder answer** for supportive housing and shelters. Answer 2 says the Supportive
   Housing Fund pays the whole capital cost and the Province owns the building, and that the Emergency Shelter Program
   funds running, not building. Answer 4 shows a 100% gap and sends the manager to "other grants (CMHC's Affordable
   Housing Fund among them)", which the tool's own rule says closed on 19 Dec 2025.
5. **The envelope is larger than the lot, and the envelope warnings are false.** Kingsway: an envelope of 138.02 × 32.82 m
   = 4,529.8 m² on a 2,873 m² lot. Powell, a perfect rectangle with setbacks 0/6/0, still warns "The setbacks leave no
   envelope inside the lot polygon that a rectangular plate fits"; so does Kingsway.
6. **Two vocabularies for one owner.** `owner_type_at_completion: "government"` (the site's own `OWNER_TYPES` value)
   produced "owner type 'government' is not a non-profit, co-op or government". The suggester also sets 30% below the
   income limits and a non-profit owner even when the target is the Supportive Housing Fund.
7. **The height tested is not the height drawn**: 17.0 m checked, 17.7 m (4.5 + 4 × 3.3) drawn, against 15.0 m.
8. **memo.md's Sources list the whole stack**: the DEOD memo cites C-2, C-2A, C-2B, C-2C, C-2C1, FM-1, CD-1 (324) and
   CD-1 (819).

### Flow problems

1. **The suggestion ignores the kind of housing.** `suggest.py` never reads `housing_type`: at Powell with the
   Supportive Housing Fund targeted it derived "4 studio, 7 one bed, 6 two bed, 1 three bed plus" and 12 replacement
   trees on a lot built to its lines. The page asks "Who are the homes for?" at stop 02 after the option is derived.
   Beds have no question in the manager's route.
2. **No supportive or shelter program in the layout**: no 24/7 desk by the entry with sight lines, staff office, staff
   washroom, clinic, dining, laundry, harm-reduction or program room. The shelter plan is "0 of 0 units" with one 40 m²
   services block.
3. **The plate is driven by GFA ÷ storeys, not unit depth.** Powell: a 36.99 × 12.98 m plate, 5.59 m deep studios on a
   1,983 m² lot; the 500 m² ground floor cannot fit a 480 m² plate, so the clinic spills upstairs and 17 studios "did not
   fit". The podium form is not offered.
4. **Studios at 33 m² + 10%**, no supportive-studio profile, no "the operator's brief".
5. **Indigenous-led does nothing for supportive housing**: `bch.ihf.program` is for independent rental only, and the
   title block prints neither Indigenous-led nor a Nation partner.
6. **No way to keep a transition house address confidential**: it is in the title, map, file names and PDF.
7. **"Is it allowed?" never asks whether the use is permitted**: "yes" for a shelter on C-2A on FSR and height alone.

## 4. What should change, ranked

1. **A program brief by housing type** (L): rooms or beds; desk, staff, clinic, meals and laundry as named blocks with
   operator-entered areas; placed on the ground floor with adjacency rules ("the desk sees the entry").
2. **Fix the shelter operating page** (S): read `operations` when units are 0 and beds > 0, report per bed, drop the
   unit-mix item.
3. **Answer 4 follows answer 2's program model** (M): for Province-owned SHF and WTHF buildings show the capital as the
   Province's and lead with the operating subsidy; never name a closed fund.
4. **Corner-lot front and the narrow-site cap** (S/M): say the cap in the finding, test both fronts and show both, never
   fail on a front the tool chose; fix the "(none)" leak and the route contradiction.
5. **Use permissibility per district** for shelter, clinic and supportive housing, from the schedules already saved (M).
6. **A derivation aware of housing type** (M): an all-studio supportive candidate, beds for a shelter, RGI and Province
   defaults when SHF is targeted.
7. **A podium plate**: a ground floor different from the floors above (M).
8. **A confidential-address mode** (S): memo, PDF and file names show a district and lot size only.
9. **A site by PID, by clicking a parcel, or by drawing a lot** (M).
10. **Indigenous-led and a Nation partner on the title block**, and an Indigenous supportive route (S/M).
11. **Envelope and height consistency; Sources filtered to the rules that apply** (S).

## 5. What would make the reviewer distrust it

- The Jervis flip: "not allowed outright" or "yes, with conditions" depending on the front the tool chose, with the cap
  unnamed. Issued to an operator, it would have sent a church site needing only a permit to rezoning.
- An envelope of 4,530 m² on a 2,873 m² lot, printed as fact.
- A shelter memo that drops the operator's $2.4M staffing and asks for a bedroom mix.
- A money page that sends a supportive-housing board after a closed CMHC fund.

What earned trust: the language is respectful and accurate throughout (no "the homeless", "clients" or "victims"; "people
experiencing homelessness", "women, gender-diverse people and children leaving violence"); "listed, not tested" is
honest; every open item names someone to ask; supportive staffing is never assumed. Usable today for a DEOD sub-area
reading; not for a shelter's or supportive project's money page or plans until defects 1 to 4 are fixed.
