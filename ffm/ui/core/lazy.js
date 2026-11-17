/* The parts the manager's first load does not carry: the paper memo (PDF and Print), the block editor (FIG 03)
   and the boundary editor (FIG 01). Each is fetched with import() the first time it is wanted; `loaded` keeps
   the module once it is in, so code that only runs while an editor is open can call it without waiting. */

export const loaded = { paper: null, blocks: null, boundary: null };

export function loadPaper() { return import("../paper.js").then(m => (loaded.paper = m)); }
export function loadBlocks() { return import("../editors/blocks.js").then(m => (loaded.blocks = m)); }
export function loadBoundary() { return import("../editors/boundary.js").then(m => (loaded.boundary = m)); }


