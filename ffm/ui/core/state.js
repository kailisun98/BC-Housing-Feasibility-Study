/* Where the page runs and what it remembers while it is open. Every object here is mutated in place by the modules
   that use it (an ES module cannot reassign another module's binding), so they are const and shared by reference.
   The walkthrough's `tour` and FIG 01's mass placement `mass` are local to tour.js and figures/cards.js. */

/* The static build (GitHub Pages): `python -m ffm pages` sets window.FFM_STATIC before the modules load, and
   core/api.js then reads data files and runs the engine in the browser. Null under the local server. */
export const STATIC = window.FFM_STATIC || null;

/* The files, the run on screen, the mode and the rules. */
export const state = {
  sites: [], options: [], rules: [],
  siteId: null, optionId: null,
  site: null, option: null,
  siteDirty: false, optionDirty: false,
  run: null,            // the last /api/run response
  runs: [],             // past runs for the site
  compareRun: null,     // run_id to diff against on the next run
  step: 1,              // the step the reader is on, for the step bar
  revisions: new Map(), // run_id -> "R1", "R2"…: the memo's revision on its site
  mode: "manager",      // who is reading: manager, architect, reader (setMode)
  view: "detailed",     // how much of the memo: summary, detailed, 3d (setView)
  issues: [],           // the site's issue notes, from the local server
};

export const PRELOAD_SITE = "998-e-19th-ave";

export const PRELOAD_OPTION = "998-e-19th-ave-as-approved";

/* The manager's route (route-stage.js, guide.js): the stop, the address and the lookup, the programs, the reading,
   the suggestion and the candidate, the manager's own figures and answers, what is busy, and whether a route row's
   card is over the memo. */
export const guide = { step: 1, address: "", lookup: null, programs: null, reading: null, suggestion: null, candidate: "funder-ready", mine: {}, answers: {}, busy: {}, over: false };

/* The boundary editor on FIG 01 (editors/boundary.js; the plan draws its handles while it is open). */
export const bnd = { open: false, ring: null, sel: null, drag: null, busy: false };

/* The block editor on FIG 03 (editors/blocks.js; a re-rendered memo closes it, and leaving architect mode). */
export const editor = { open: false, level: 0, zones: null, sel: null, dirty: false, result: null, timer: 0, busy: false, applied: false, grid: 0.1, blank: false };
