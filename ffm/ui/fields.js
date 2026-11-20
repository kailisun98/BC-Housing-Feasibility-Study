/* Every input once (FIELDS), and its views: the Site and Option schedules (SITE_FIELDS, OPTION_FIELDS), the
   marks and explanations (FIELD_META), the manager's questions (GUIDE_FIELDS), the money (FINANCE_FIELDS) and
   the answers asked of a person (ANSWERS). A new input is one entry in FIELDS. */

export const TRI = "tri";

/* Every input the tool asks for, once (16 Nov 2026; before, six lists described overlapping fields). Each entry says
   which file it belongs to (`on`), where the architect's schedule shows it (`group`, and `rowOf` for figures read
   together), who reads it (`need`: "run" the engine cannot build the memo without it, "rule" a rule reads it and a
   blank comes back uncertain, "figure" only the drawings, nothing a note for people; `reads`: the checks in
   ffm/checks.py that read it, so the schedule can cite their rules as A1, C2; `ref` a word where no rule does), why
   (`info`), where the manager is asked it (`ask`: the stop, the question, who answers), whether it is one of the
   suggested figures at stop 2 (`figure`: its group, its place, its kind) or one of the money figures (`money`).
   The Site and Option schedules, the manager's questions, the four-figure block, "All 21 figures", the money fields
   and every summary read this one list; SITE_FIELDS, OPTION_FIELDS, FIELD_META, GUIDE_FIELDS, FINANCE_FIELDS and
   ANSWERS below are views of it. */
const OWNER_TYPES = [["", "Not sure"], ["church", "A church"], ["society", "A non-profit society"], ["co-op", "A housing co-operative"],
  ["first_nation", "A First Nation"], ["municipality", "The City"], ["government", "The Province or Canada"], ["private", "Private"]];

const SITE_CONTROL = [["", "Not sure"], ["letter_of_intent", "Letter of intent"], ["purchase_agreement", "Purchase agreement"],
  ["council_resolution", "Council resolution"], ["finalized", "Finalized"], ["none", "None yet"]];

const TENURES = [["social_housing", "Social housing"], ["secured_market_rental", "Secured market rental"], ["other", "Other"]];

const FIELDS = [
  // ---- the site
  { on: "site", key: "id", group: "Identity", label: "Site id", type: "slug", need: "run", ref: "file",
    help: "Letters, digits and hyphens; names the file and the outputs folder.",
    info: "Names the file (sites/<id>.json or options/<id>.json) and the outputs folder. Letters, digits and hyphens." },
  { on: "site", key: "address", group: "Identity", label: "Address", type: "text", need: "", ref: "title",
    info: "Printed as the memo's title; python -m ffm context geocodes it to draw the surroundings." },
  { on: "site", key: "municipality", group: "Identity", label: "Municipality", type: "text", need: "", ref: "note",
    info: "A note: the rule stack is written for the City of Vancouver." },
  { on: "site", key: "zoning_district", group: "Identity", label: "Zoning district", type: "text", need: "run",
    reads: ["district_outright_fsr", "district_outright_height", "district_setbacks", "ssmuh_minimum_units"],
    help: "As written in the by-law: RM-1, RS-1, RT-3, R1-1 …",
    info: "The district schedule that applies without a rezoning, as the by-law writes it. The rule stack holds the outright limits read from the schedules for RM-1/RM-1N, RM-3, RM-3A, RM-4, the RM-5 family, RT-3, R1-1 (multiplex), C-2, C-2A, C-2B, C-2C, C-2C1, RR-1, RR-2A, RR-2B and RR-3A/3B/3C (with their social housing, rental and site-size figures), and the rest of the RT family entered unverified (the memo says so), plus the SSMUH rule for R1-1, RS and RT. A CD-1 is its own by-law: its rules are matched on the CD-1 number (CD-1 (324) is in, read from its by-law; CD-1 (819) from its referral report, unverified). A district or CD-1 not in the stack reads 'not assessed', says so, and the rough envelope stands in." },
  { on: "site", key: "cd1_bylaw_number", group: "Identity", label: "CD-1 number", type: "text", need: "",
    reads: ["district_outright_fsr", "district_outright_height", "district_setbacks"],
    help: "For a CD-1 site only: 324 for CD-1 (324). The lookup fills it from the City's zoning data.",
    info: "Each CD-1 is its own by-law, so a CD-1 site is matched to its rules by this number and no other: CD-1 (324)'s rules never apply to CD-1 (819). Blank on a CD-1 site, no by-law can be matched and the outright answer reads 'not assessed'. Leave it blank for any other district." },
  { on: "site", key: "cd1_sub_area", group: "Identity", label: "CD-1 sub-area", type: "text", need: "",
    reads: ["district_outright_fsr"],
    help: "Where the CD-1 by-law sets figures by sub-area: B for 1010 Expo Blvd in CD-1 (324).",
    info: "Some CD-1 by-laws fix the floor area per sub-area drawn on their Schedule A (CD-1 (324): sub-area A 19,300 m², B 23,600 m² of residential floor area). Read the site's sub-area off that map; blank, the floor area reads 'uncertain' and says so." },
  { on: "site", key: "site_area_m2", group: "Lot", rowOf: "lot", label: "Area (m²)", type: "number", need: "run",
    reads: ["district_outright_fsr", "ssmuh_minimum_units", "tree_replacement"],
    info: "Divides the option's floor area into an FSR, sets Schedule C's minimum tree count (2,551 to 2,900 m² needs 20 trees) and sizes the outright mass." },
  { on: "site", key: "frontage_m", group: "Lot", rowOf: "lot", label: "Frontage (m)", type: "number", need: "run", ref: "drawings",
    info: "With the depth, the rectangle the massing is drawn in. For an irregular lot use the rectangle with the same area and say so in the notes; the FSR still uses the recorded area." },
  { on: "site", key: "depth_m", group: "Lot", rowOf: "lot", label: "Depth (m)", type: "number", need: "run", ref: "drawings",
    info: "With the frontage, the rectangle the massing is drawn in; the street is along the frontage, the lane behind the depth." },
  { on: "site", key: "in_former_community_vision_area", group: "Policy areas", label: "In a former Community Vision area", type: TRI, need: "rule",
    reads: ["rezoning_policy_social_housing"],
    ask: { stop: 1, q: "Inside a former Community Vision area?", who: "you, from Map 1 of the Interim Rezoning Policy",
      why: "Decides whether the social housing rezoning policy, and its staff benchmark, applies.",
      where: ["Map 1 of the policy", "https://guidelines.vancouver.ca/policy-rezoning-former-community-visions-areas.pdf"] },
    info: "Map 1 of the Interim Rezoning Policy for Social Housing (1 Nov 2023, amended 31 Mar 2026). Inside the map, 100% social housing can rezone to CD-1 against a staff benchmark (here about 19.9 to 21.3 m and FSR 3.0). Outside it, the Affordable Housing Policies (1989) or an area plan apply and this rule reads 'not applicable'." },
  { on: "site", key: "in_transit_oriented_area", group: "Policy areas", label: "In a transit-oriented area", type: TRI, need: "rule",
    reads: ["toa_status", "ssmuh_minimum_units"],
    ask: { stop: 1, q: "Inside a transit-oriented area?", who: "you, from the City's TOA map",
      why: "Inside one, the Province sets a minimum height and density by tier.",
      where: ["the City's June 2024 release on the areas", "https://vancouver.ca/news-calendar/city-passes-housing-transit-friendly-action-june-2024.aspx"] },
    info: "Bill 47 (2023): inside a provincially designated transit-oriented area the City may not refuse the minimum height and density for the tier. Vancouver designated 29 such areas in June 2024, around SkyTrain stations and bus exchanges. Check the City's TOA map; 'Not sure' comes back as uncertain." },
  { on: "site", key: "toa_tier", group: "Policy areas", label: "Transit-oriented area tier", type: "select", need: "rule", reads: ["toa_status"],
    // short enough for the architect's schedule (17 Nov 2026: "Tier 4 · bus exchange, within 200 m" was cut in it)
    options: [["", "Not sure"], ["1", "1 · SkyTrain, 200 m"], ["2", "2 · SkyTrain, 400 m"], ["3", "3 · SkyTrain, 800 m"],
      ["4", "4 · bus exchange, 200 m"], ["5", "5 · bus exchange, 400 m"]],
    ask: { stop: 1, q: "Which tier?", who: "you, from the same map", when: site => site.in_transit_oriented_area === true,
      why: "Sets the minimum: 20, 12 or 8 storeys, by the distance to the station or exchange." },
    info: "Distance bands: around a SkyTrain station Tier 1 within 200 m, minimum allowable 20 storeys; Tier 2 200 to 400 m, 12 storeys; Tier 3 400 to 800 m, 8 storeys. Around a bus exchange (the Kootenay Loop, say) Tier 4 within 200 m, 12 storeys; Tier 5 200 to 400 m, 8 storeys. The tier comes from the City's TOA map, which the tool does not read." },
  { on: "site", key: "frequent_bus_stop_within_400m", group: "Policy areas", label: "Frequent bus stop within 400 m", type: TRI, need: "", ref: "note",
    info: "Recorded for the record: no rule in the stack reads it yet. It will matter when frequent-transit policies are coded." },
  { on: "site", key: "has_water_and_sewer", group: "Policy areas", label: "Water and sewer service", type: TRI, need: "rule", reads: ["ssmuh_minimum_units"],
    ask: { stop: 1, q: "Water and sewer service?", who: "you",
      why: "The small-scale multiplex minimums apply only on a serviced lot.", where: ["the site survey or the City's records"] },
    info: "The Small-Scale Multi-Unit Housing minimums (Bill 44) apply only where the lot has water and sewer service; 'No' switches that rule off." },
  { on: "site", key: "existing_trees_on_site", group: "Trees", label: "Existing trees on site", type: "trees", need: "rule", reads: ["tree_replacement"],
    info: "Protection of Trees By-law 9958. The survey must cover every tree of 20 cm DBH or more on the site, within 2 m of the boundary and on the adjoining street. Schedule A sets the protection barrier by trunk diameter (40 cm: 2.4 m, which the massing must leave clear); Schedule C sets how many trees the site must have after development, by area; each missing tree is $1,000 cash in lieu. No survey on file: the rule says so and returns uncertain." },
  { on: "site", key: "street_trees.count", group: "Trees", label: "Street trees (count)", type: "number", int: true, need: "figure", ref: "drawings",
    info: "Drawn along the frontage in the figures; no rule reads it." },
  { on: "site", key: "owner", group: "Owner", label: "Owner", type: "text", need: "", reads: ["dcl_cac"],
    info: "Printed in the memo's inputs." },
  // the architect's schedule offers the manager's choices (17 Nov 2026: it was free text showing "municipality")
  { on: "site", key: "owner_type", group: "Owner", label: "Owner type", type: "select", options: OWNER_TYPES, need: "", reads: ["dcl_cac"],
    ask: { stop: 1, q: "Who owns the land?", who: "you", kind: "select", options: OWNER_TYPES,
      why: "A church, society or government owner lets the money count the land at a nominal value.",
      where: ["the land title, or BC Assessment", "https://www.bcassessment.ca/"] },
    info: "A note for the memo: church, society, municipality, private. The DCL exemption for church use is read from the referral report, not from this field. The pro-forma carries the land at a nominal value where the owner is a church, a society or a government on a long lease." },
  { on: "site", key: "keep_existing_buildings", group: "Owner", label: "The buildings on the lot stay", type: TRI, need: "rule", ref: "open item",
    ask: { stop: 1, q: "Do the buildings on the lot stay?", who: "you, then the architect",
      why: "The drawings assume a clear lot; a building that stays changes the massing." },
    info: "The massing is drawn on a clear lot. Yes means a building stays and the architect must draw the kept footprint; No means the lot is cleared; Not sure becomes an open item with the manager's name." },
  { on: "site", key: "land_tenure_plan", group: "Owner", label: "Land tenure plan", type: "text", need: "rule", reads: ["chf_fit"],
    help: "Write “to confirm” if it is not settled; the funders' checks read that honestly.",
    ask: { stop: 1, q: "How will the land be held?", who: "you", placeholder: "e.g. owned, or a 60-year nominal lease",
      examples: ["owned by the society", "a 60-year lease at a nominal rent", "a 99-year lease at a nominal rent", "to confirm"],
      why: "The Community Housing Fund needs ownership, or a lease of 60 years or more at a nominal rent.", where: ["the owner's agreement"] },
    info: "Who will hold the land. The Community Housing Fund needs a lease of at least 60 years at nominal value, or ownership. Write 'to confirm' while it is unsettled: the check then returns uncertain instead of guessing. The option's own tenure plan overrides this one." },
  { on: "site", key: "notes", group: "Owner", label: "Notes", type: "textarea", need: "", ref: "note",
    info: "Placeholders, assumptions and what still needs checking. The memo prints them." },
  // the front of a corner lot: asked at stop 1 only where the lookup found two streets; not a schedule row
  { on: "site", key: "front_street", label: "Which street is the front", type: "select", need: "rule", ref: "drawings",
    ask: { stop: 1, q: "Which street is the front?", who: "you, or the architect confirms it", when: site => cornerStreets(site).length > 0,
      why: "Sets which yards are front, side and rear, and so the envelope.", where: ["the survey, or the address the City lists"] },
    info: "The front street sets the yards, the envelope and the massing; choosing the other street turns the lot to it (the site's front_face)." },
  // a lane behind the lot as fronted: RT-3 takes the distance to the lane's centre line off the rear yard (s.3.1.2.17)
  { on: "site", key: "context.lane_behind", group: "Lot", label: "A lane behind the lot", type: TRI, need: "rule", reads: ["district_setbacks"],
    ask: { stop: 1, q: "A lane behind the lot, opposite the front?", who: "you, or the architect from the survey",
      why: "A lane behind can shorten the rear yard (RT-3 takes off the distance to its centre line).", where: ["the map above, or the survey"] },
    info: "Where the rear of the lot (the side opposite the front) runs along a lane. RT-3 reduces the 20.0 m rear yard by the distance from the rear property line to the lane's ultimate centre line (s.3.1.2.17), taken as 3.05 m, half a standard 6.1 m lane, unless the site gives its own figure (context.lane_to_centre_line_m). The open data the lookup reads carry no lanes, so a person says. Not sure leaves the full rear yard." },

  // ---- the option
  { on: "option", key: "id", group: "Option", label: "Option id", type: "slug", need: "run", ref: "file",
    help: "Start it with the site id so it lists under the site.",
    info: "Names the file (sites/<id>.json or options/<id>.json) and the outputs folder. Letters, digits and hyphens." },
  { on: "option", key: "name", group: "Option", label: "Name", type: "text", need: "", ref: "title",
    info: "How the option is listed and printed; say when it is hypothetical." },
  { on: "option", key: "proponent", group: "Option", label: "Proponent", type: "text", need: "", ref: "title",
    info: "The society, co-operative or body that will own and run the housing; printed in the memo's title block." },
  { on: "option", key: "proponent_type", group: "Option", label: "Proponent type", type: "select", need: "rule", reads: ["chf_fit", "bc_builds_fit"],
    options: [["non_profit_society", "Non-profit society"], ["housing_cooperative", "Housing co-operative"], ["municipal_housing_provider", "Municipal housing provider"],
      ["first_nation", "First Nation"], ["private", "Private"], ["other", "Other"]],
    info: "The Community Housing Fund takes non-profit societies, housing co-operatives, municipal housing providers and First Nations; private or other proponents fail that check. BC Builds takes any proponent that meets its below-market terms." },
  { on: "option", key: "developer_partner", group: "Option", label: "Teamed with a developer or builder", type: TRI, need: "rule", reads: ["bc_builds_fit"],
    ask: { stop: 2, q: "Teamed with a developer or builder?", who: "you" },
    info: "BC Builds asks a non-profit to team with a developer or builder; a 'No' here fails that check for a non-profit." },
  { on: "option", key: "storeys", group: "Building", rowOf: "b1", label: "Storeys", type: "number", int: true, need: "run",
    reads: ["district_outright_height", "code_basis_flags", "toa_status"], figure: { g: "envelope", n: 2, kind: "int" },
    info: "Tested against the transit-oriented minimum for the tier and the code basis (Part 9 up to three storeys and 600 m², Part 3 above). Storeys × floor to floor should land near the height; where the stated height is taller, the massing uses the stated height and says the extra is parapet or a taller ground floor." },
  { on: "option", key: "height_m", group: "Building", rowOf: "b1", label: "Height (m)", type: "number", need: "run",
    reads: ["district_outright_height", "rezoning_policy_social_housing"], figure: { g: "envelope", n: 3, kind: "number" },
    info: "Tested against the district's outright maximum (RM-1: 10.7 m) and, in a rezoning, the staff benchmark (here 19.9 to 21.3 m). Over the outright limit means a rezoning is needed; over the benchmark means a bigger ask of staff." },
  { on: "option", key: "floor_to_floor_m", group: "Building", rowOf: "b1", label: "Floor to floor (m)", type: "number", need: "figure", ref: "drawings",
    figure: { g: "drawing", n: 18, kind: "number" },
    info: "Sizes the storeys in the section and the Revit floor plates. 3.0 to 3.3 m is usual for wood-frame residential." },
  { on: "option", key: "gfa_m2", group: "Building", rowOf: "b2", label: "Floor area (m²)", type: "number", need: "run",
    reads: ["district_outright_fsr", "bc_builds_fit"], figure: { g: "envelope", n: 4, kind: "number", label: "Floor area (m²)" },
    info: "Gross floor area over all storeys. Divided by the site area it is the FSR, tested against the outright maximum (RM-1: 1.2) and the benchmark (about 3.0). The massing spreads it evenly over the storeys." },
  { on: "option", key: "residential_gfa_m2", group: "Building", rowOf: "b2", label: "Residential floor area (m²)", type: "number", need: "rule", reads: ["unit_area_flags"],
    info: "With the non-residential area, BC Builds' cap of 30% non-residential floor area." },
  { on: "option", key: "non_residential_gfa_m2", group: "Building", rowOf: "b2", label: "Non-residential floor area (m²)", type: "number", need: "rule", reads: ["bc_builds_fit"],
    info: "Childcare, a hall, a church, shops. BC Builds caps non-residential space at 30% of the floor area." },
  { on: "option", key: "setbacks_m.front", group: "Building", rowOf: "sb", label: "Front setback (m)", type: "number", need: "rule", reads: ["district_setbacks"],
    figure: { g: "drawing", n: 19, kind: "number" },
    info: "The yards are zoning: where the rules hold the district's schedule (a confirmed one), the front, rear and side setbacks are tested against its minimum yards; where they do not, the memo's open items say the yards were not checked. They also size the envelope the masses are drawn in." },
  { on: "option", key: "setbacks_m.rear", group: "Building", rowOf: "sb", label: "Rear setback (m)", type: "number", need: "rule", reads: ["district_setbacks"],
    figure: { g: "drawing", n: 20, kind: "number" },
    info: "The rear yard, usually the lane side; tested against the schedule's minimum where the rules hold one, and it leaves room for the retained trees' barriers." },
  { on: "option", key: "setbacks_m.side", group: "Building", rowOf: "sb", label: "Side setback (m)", type: "number", need: "rule", reads: ["district_setbacks"],
    figure: { g: "drawing", n: 21, kind: "number" },
    info: "Applied on both sides (a corner lot's flanking street is not told apart yet); the envelope's width is the frontage less twice this." },
  { on: "option", group: "Building", type: "envelope-live" },
  { on: "option", key: "units.studio", group: "Homes", rowOf: "u", label: "Studios", type: "number", int: true, need: "rule", reads: ["family_unit_share"],
    figure: { g: "homes", n: 5, kind: "int" },
    info: "The bedroom mix. In a rezoning at least 35% of units must have two or more bedrooms, and from 27 Oct 2026 at least 5% three or more. Leave the mix blank and the family-unit rule returns uncertain." },
  { on: "option", key: "units.one_bed", group: "Homes", rowOf: "u", label: "1-bed homes", type: "number", int: true, need: "rule", reads: ["family_unit_share"],
    figure: { g: "homes", n: 6, kind: "int" },
    info: "Counted toward the total; the family share is two-bedroom-plus over all units." },
  { on: "option", key: "units.two_bed", group: "Homes", rowOf: "u", label: "2-bed homes", type: "number", int: true, need: "rule", reads: ["family_unit_share"],
    figure: { g: "homes", n: 7, kind: "int" },
    info: "Counts as a family unit: at least 35% of units must have two or more bedrooms in a rezoning." },
  { on: "option", key: "units.three_bed_plus", group: "Homes", rowOf: "u", label: "3-bed+ homes", type: "number", int: true, need: "rule", reads: ["family_unit_share"],
    figure: { g: "homes", n: 8, kind: "int" },
    info: "Counts as a family unit, and from 27 Oct 2026 at least 5% of units must have three or more bedrooms." },
  { on: "option", group: "Homes", type: "units-live" },
  { on: "option", key: "tenure", group: "Tenure", label: "Tenure", type: "select", need: "run",
    reads: ["rezoning_policy_social_housing", "social_housing_definition", "below_market_rental_policy", "dcl_cac"], options: TENURES,
    ask: { stop: 2, q: "Tenure", who: "you" },
    info: "Social housing, as the DCL By-law defines it, is exempt from development cost levies and community amenity contributions and rezones under the social housing policy. Secured market rental answers to the below-market rental policy instead (20% of floor area at 20% below the CMHC average)." },
  { on: "option", key: "share_below_hils", group: "Tenure", rowOf: "t1", label: "Share below HILs", type: "number", share: true, need: "rule",
    reads: ["social_housing_definition"], help: "0.30 = 30%", figure: { g: "terms", n: 13, kind: "number" },
    info: "Housing Income Limits are BC Housing's yearly income ceilings by unit size. The City's social housing definition needs at least 30% of the units for households below the HILs, at rents of at most 30% of income. 0.30 means 30%." },
  { on: "option", key: "max_rent_share_of_income", group: "Tenure", rowOf: "t1", label: "Max rent / income", type: "number", share: true, need: "rule",
    reads: ["social_housing_definition"], help: "0.30 = 30%",
    info: "The rent ceiling for the HILs units: at most 30% of household income under the City's definition." },
  { on: "option", key: "housing_agreement_years", group: "Tenure", rowOf: "t1", label: "Agreement (years)", type: "number", int: true, need: "rule",
    reads: ["social_housing_definition"], figure: { g: "terms", n: 14, kind: "int" },
    info: "The City secures social housing by a housing agreement for the longer of 60 years and the life of the building; BC Builds' leases run 60 to 99 years." },
  { on: "option", key: "owner_type_at_completion", group: "Tenure", label: "Owner at completion", type: "select", need: "rule", reads: ["social_housing_definition"],
    options: [["", "Not sure"], ["non_profit_society", "Non-profit society"], ["housing_cooperative", "Housing co-operative"],
      ["city", "City"], ["province", "Province"], ["canada", "Canada"], ["private", "Private"]],
    info: "The social housing definition needs the building owned by a non-profit society, a housing co-operative, the City, the Province or Canada. A private owner fails it." },
  { on: "option", key: "target_programs", group: "Funding", label: "Target programs", type: "programs", need: "rule", reads: ["chf_fit", "bc_builds_fit"],
    info: "The funders whose fit decides the memo's second answer. Programs left unticked are still run and listed in the ledger as information." },
  { on: "option", key: "rent_tiers_units.market", group: "Funding", rowOf: "tiers", label: "Market units", type: "number", int: true, need: "rule",
    reads: ["chf_fit"], figure: { g: "homes", n: 9, kind: "int" },
    info: "The Community Housing Fund's mix: 30% of units at market-ish rents for low to moderate incomes (2025 limits $85,870 under two bedrooms, $138,770 two bedrooms and up), 50% rent-geared-to-income, 20% deep subsidy, each within 2 points. Blank tiers leave the fund's check uncertain." },
  { on: "option", key: "rent_tiers_units.rgi", group: "Funding", rowOf: "tiers", label: "RGI units", type: "number", int: true, need: "rule",
    reads: ["chf_fit"], figure: { g: "homes", n: 10, kind: "int" },
    info: "Rent-geared-to-income units: 50% of the total under the Community Housing Fund's 30/50/20 mix." },
  { on: "option", key: "rent_tiers_units.deep_subsidy", group: "Funding", rowOf: "tiers", label: "Deep-subsidy units", type: "number", int: true, need: "rule",
    reads: ["chf_fit"], figure: { g: "homes", n: 11, kind: "int" },
    info: "Deep-subsidy (shelter-rate) units: 20% of the total under the Community Housing Fund's 30/50/20 mix." },
  { on: "option", key: "accessible_units", group: "Funding", rowOf: "f2", label: "Accessible units", type: "number", int: true, need: "rule",
    reads: ["chf_fit"], figure: { g: "homes", n: 12, kind: "int" },
    info: "The Community Housing Fund needs at least 5% of units accessible (adaptable units are counted separately by the design guidelines)." },
  { on: "option", key: "below_market_unit_share", group: "Funding", rowOf: "f2", label: "Below-market share", type: "number", share: true, need: "rule",
    reads: ["bc_builds_fit", "below_market_rental_policy"], help: "of units, 0–1", figure: { g: "terms", n: 15, kind: "number" },
    info: "BC Builds: at least 20% of the units at least 20% below market rent; 1.0 means every unit. The City's below-market rental policy for secured market rental counts floor area instead." },
  { on: "option", key: "below_market_discount", group: "Funding", rowOf: "f2", label: "Discount to market", type: "number", share: true, need: "rule",
    reads: ["bc_builds_fit", "below_market_rental_policy"], help: "0.20 = 20%", figure: { g: "terms", n: 16, kind: "number" },
    info: "The discount of those units to market: at least 20% for BC Builds (0.20)." },
  { on: "option", key: "site_control", group: "Funding", label: "Site control", type: "select", need: "rule", reads: ["chf_fit"], options: SITE_CONTROL,
    ask: { stop: 2, q: "Site control", who: "you" },
    info: "Readiness for a funding call. The Community Housing Fund accepts a finalized deal, a purchase agreement, a letter of intent or a council resolution; 'none yet' fails the readiness bar. Construction must also be able to start within 18 months of an award." },
  { on: "option", key: "land_tenure_plan", group: "Funding", label: "Land tenure plan", type: "text", need: "rule", reads: ["chf_fit"],
    help: "Leave blank to use the site's; write “to confirm” if unsettled.",
    info: "Who will hold the land. The Community Housing Fund needs a lease of at least 60 years at nominal value, or ownership. Write 'to confirm' while it is unsettled: the check then returns uncertain instead of guessing. The option's own tenure plan overrides the site's." },
  { on: "option", key: "replacement_trees_proposed", group: "Trees", label: "Replacement trees proposed", type: "number", int: true, need: "rule",
    reads: ["tree_replacement"], figure: { g: "drawing", n: 17, kind: "int", label: "Replacement trees" },
    info: "Trees planted after construction. Retained plus replacement trees must reach Schedule C's minimum for the site area; each tree short is $1,000 cash in lieu." },
  { on: "option", key: "finance.land_cost_cad", group: "Money", rowOf: "fin", label: "Land ($)", type: "number", need: "rule", ref: "money", money: true,
    info: "The pro-forma's land line. Leave it blank where the owner is a church, a society or a government on a long lease: the assumptions layer carries the land at a nominal value. On a private site enter the BC Assessment value or the agreed price; blank there leaves the money answer unsure." },
  { on: "option", key: "finance.equity_cad", group: "Money", rowOf: "fin", label: "Equity ($)", type: "number", need: "rule", ref: "money", money: true,
    info: "Cash the proponent brings. Blank means none; the funding stack is then grants plus the debt the net operating income can carry." },
  { on: "option", key: "finance.other_grants_cad", group: "Money", rowOf: "fin", label: "Other grants ($)", type: "number", need: "rule", ref: "money", money: true,
    info: "Grants beyond the Community Housing Fund's provisional per-unit grant, which the pro-forma counts on its own when the fund is targeted." },
  { on: "option", key: "rezoning_path", group: "Rezoning path", label: "Rezoning path", type: "text", need: "rule",
    reads: ["district_outright_fsr", "district_outright_height"], help: "Empty means outright only.", figure: { g: "envelope", n: 1, kind: "text" },
    info: "Blank means the option must fit outright. Name a path (CD-1 under the Interim Rezoning Policy for Social Housing, an ODP amendment) and the memo answers 'by rezoning' through that policy; the outright rules then read as the ask, not as a fail." },
  { on: "option", key: "notes", group: "Notes", label: "Notes", type: "textarea", need: "", ref: "note",
    info: "Placeholders, assumptions and what still needs checking. The memo prints them." },
  // read by a rule, not shown in the schedule
  { on: "option", key: "parking_spaces", label: "Parking spaces", type: "number", need: "", reads: ["parking_minimums"],
    info: "No minimum off-street parking applies in Vancouver since June 2024; the count is reported as information. Bicycle spaces are set by the Parking By-law at the development permit stage." },
  { on: "option", key: "bicycle_spaces", label: "Bicycle spaces", type: "number", need: "", reads: ["parking_minimums"],
    info: "Reported as information; the Parking By-law sets the minimum at the development permit stage." },
];

/* The schedule's layout for one file: its groups in order, the fields of a row together. */
function layoutOf(on) {
  const groups = [];
  for (const f of FIELDS.filter(x => x.on === on && x.group)) {
    let g = groups.find(x => x.group === f.group);
    if (!g) groups.push(g = { group: f.group, fields: [] });
    if (f.rowOf) {
      let r = g.fields.find(x => x.row && x.id === f.rowOf);
      if (!r) g.fields.push(r = { row: true, id: f.rowOf, fields: [] });
      r.fields.push(f);
    } else g.fields.push(f);
  }
  return groups;
}

export const SITE_FIELDS = layoutOf("site");

export const OPTION_FIELDS = layoutOf("option");

export const fieldOf = (on, key) => FIELDS.find(f => f.on === on && f.key === key) || null;

/* A share (0 to 1 in the file) is shown and typed as a percentage on the manager's stage (17 Nov 2026: "Share below
   HILs 0.7"); these two convert between the file's figure and the one on screen. */
export const isShare = key => !!(fieldOf("option", key) || {}).share;
export const shareToScreen = (key, v) => (isShare(key) && typeof v === "number" ? Math.round(v * 1000) / 10 : v);
export const shareFromScreen = (key, v) => (isShare(key) && typeof v === "number" && Number.isFinite(v) ? Math.round(v * 10) / 1000 : v);

/* A coded value in words, from the field's own options (non_profit_society → "non-profit society"), so no
   identifier from a file reaches a sentence on screen or on paper. */
export function optWord(on, key, v) {
  if (v == null || v === "") return "";
  const f = fieldOf(on, key);
  // the field's options, else the ones its question offers (the owner's type: "municipality" → "the City")
  const opts = (f && (f.options || (f.ask && f.ask.options))) || [];
  const o = opts.find(([x]) => String(x) === String(v));
  const w = o ? o[1] : String(v).replace(/_/g, " ");
  // the first letter only goes to lower case, so a proper noun after it keeps its capital ("the City")
  return w.charAt(0).toLowerCase() + w.slice(1);
}

/* Who reads a field and why, by key (the site's entry where both files share a key). */
const FIELD_META = {};

for (const f of FIELDS) if (f.key && !FIELD_META[f.key]) FIELD_META[f.key] = { need: f.need || "", info: f.info, reads: f.reads || [], ref: f.ref || "" };

/* The suggested figures the manager decides on at stop 2, in the order the memo reads them: [key, label, kind]. */
export const GUIDE_FIELDS = FIELDS.filter(f => f.figure).sort((a, b) => a.figure.n - b.figure.n).map(f => [f.key, f.figure.label || f.label, f.figure.kind]);

/* The three money figures only the manager knows: [key, label]. */
export const FINANCE_FIELDS = FIELDS.filter(f => f.money).map(f => [f.key, f.label]);

/* What the rules leave to a person, asked in the flow: the site's at stop 1, the option's at stop 2. */
/* (20 Nov 2026) `why`: what the answer changes, in a few words; `where`: [where to find it, its public URL if any];
   `examples`: suggestions a text answer offers (a datalist), for a question that takes a phrase. */
export const ANSWERS = Object.fromEntries(FIELDS.filter(f => f.ask).map(f => [f.key, {
  on: f.on, stop: f.ask.stop, who: f.ask.who, when: f.ask.when || null, label: f.ask.q, placeholder: f.ask.placeholder || "",
  why: f.ask.why || "", where: f.ask.where || null, examples: f.ask.examples || null,
  kind: f.ask.kind || (f.type === TRI ? "tri" : f.type === "select" ? "select" : "text"), options: f.ask.options || f.options || [] }]));

const NEED_WORD = { run: "needed to run", rule: "read by a rule; blank means uncertain", figure: "drawings only" };

/* The CD-1 number of a site zoned CD-1 (as rules_loader.cd1_number): the site's cd1_bylaw_number, else the number in
   "CD-1 (324)"; null for any other district or a CD-1 with no number known. */
export function cd1Of(district, given) {
  const m = String(district || "").match(/^\s*CD-1(?![0-9A-Za-z])\s*(?:\(\s*([0-9A-Za-z]+)\s*\))?/i);
  if (!m) return null;
  let v = given != null && given !== "" ? String(given).trim() : (m[1] || "");
  if (!v) return null;
  const f = Number(v);
  if (Number.isFinite(f) && Number.isInteger(f)) v = String(f);
  return v.toUpperCase();
}

/* The site's district as the rules read it (rules_loader.district_of): "CD-1 (324)" for a CD-1 whose number is known. */
export function districtOf(site) {
  const d = (site && site.zoning_district) || "";
  const n = cd1Of(d, site && site.cd1_bylaw_number);
  return n ? `CD-1 (${n})` : d;
}

/* A rule applies to this site's district, or to every district. A rule keyed to CD-1 numbers (applies_to_cd1) applies
   only to a CD-1 site with one of them, as Rule.applies_to in the engine. */
export function appliesHere(r, district, cd1) {
  const nums = r.applies_to_cd1 || [];
  if (nums.length) {
    const n = cd1Of(district, cd1);
    return n != null && nums.some(x => String(x).trim().toUpperCase() === n);
  }
  const ds = r.applies_to_districts || [];
  if (!ds.length || ds.includes("*")) return true;
  const d = String(district || "").toUpperCase();
  return ds.some(x => x.toUpperCase() === d || (d.startsWith(x.toUpperCase() + "-") && !x.includes("-")));
}

/* The two streets of a corner lot, from the lookup's parcel record; empty for a lot on one street. */
export function cornerStreets(site) {
  const st = site && site.parcel && site.parcel.street;
  if (!st || !st.cross_street || !st.name) return [];
  return [st.name, st.cross_street.name];
}
