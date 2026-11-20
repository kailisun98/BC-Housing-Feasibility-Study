/* First Read, the site. The pages read without script; this marks the current page in the top bar, reveals sections as
   they arrive, and keeps the hero's "01 / 05" counter honest. Nothing here calculates a rule. */

(() => {
  document.documentElement.classList.add("js");

  // the page the reader is on
  const here = (location.pathname.split("/").pop() || "index.html").replace(/^$/, "index.html");
  document.querySelectorAll(".nav-links a").forEach(a => {
    const to = (a.getAttribute("href") || "").replace(/^\.\/$/, "index.html").replace(/^\.\//, "");
    const same = to === here || (here === "home.html" && to === "index.html") || (here === "index.html" && to === "./");
    if (same) a.setAttribute("aria-current", "page");
  });

  // the hero's massing builds itself the first time the page is actually seen: a tab opened in the background
  // would otherwise run the build unwatched, so it waits for the page to become visible
  const iso = document.querySelector(".hero-iso");
  if (iso) {
    const play = () => iso.classList.add("play");
    if (document.visibilityState === "visible") play();
    else document.addEventListener("visibilitychange", function once() { if (document.visibilityState === "visible") { document.removeEventListener("visibilitychange", once); play(); } });
  }

  // sections arrive
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const items = Array.from(document.querySelectorAll(".reveal"));
  if (!reduce && "IntersectionObserver" in window && items.length) {
    // any edge inside the window reveals a section: 8% of a tall section was a screenful of scrolling, so a whole
    // viewport stayed blank for more than a second (17 Nov 2026)
    const io = new IntersectionObserver(entries => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0 });
    items.forEach(el => io.observe(el));
    // if the observer is slow (a background tab, a print preview), what is already on screen shows anyway;
    // what is below the fold still waits to be scrolled to
    const inView = el => el.getBoundingClientRect().top < window.innerHeight;
    setTimeout(() => items.forEach(el => { if (inView(el)) el.classList.add("in"); }), 1500);
    window.addEventListener("beforeprint", () => items.forEach(el => el.classList.add("in")));
  } else items.forEach(el => el.classList.add("in"));

  // the section index in the hero's foot (five links) marks the numbered section the reader is in
  const index = document.querySelector(".hero-foot .counter");
  const secs = Array.from(document.querySelectorAll("main .sec[data-n]"));
  if (index && secs.length && "IntersectionObserver" in window) {
    const links = Array.from(index.querySelectorAll("a[href^='#']"));
    const io = new IntersectionObserver(entries => {
      for (const e of entries) if (e.isIntersecting) {
        const here = "#" + e.target.id;
        links.forEach(a => { if (a.getAttribute("href") === here) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current"); });
      }
    }, { rootMargin: "-40% 0px -50% 0px" });
    secs.forEach(s => io.observe(s));
  }

  // connectors: in a diagram marked [data-links], every node with data-to="id id…" gets a line to each node it names,
  // drawn in an SVG under the nodes from their boxes as laid out, and drawn again whenever the diagram's box changes
  // (a wider window, a font arriving). A target to the right is reached from the source's right side to its left, a
  // target below from bottom to top. Nothing here is a rule; the lines only show who hands what to whom.
  const NS = "http://www.w3.org/2000/svg";
  const draw = root => {
    let svg = root.querySelector(":scope > svg.links");
    if (!svg) { svg = document.createElementNS(NS, "svg"); svg.setAttribute("class", "links"); svg.setAttribute("aria-hidden", "true"); svg.setAttribute("focusable", "false"); root.prepend(svg); }
    if (getComputedStyle(svg).display === "none") return;
    const o = root.getBoundingClientRect();
    svg.setAttribute("width", o.width); svg.setAttribute("height", o.height);
    let lines = "", heads = "";
    const f = n => n.toFixed(1);
    const head = (x, y, dx, dy) => {      // a chevron at (x, y) pointing along (dx, dy)
      const l = Math.hypot(dx, dy) || 1, ux = dx / l, uy = dy / l, s = 6.5;
      const ax = x - ux * s - uy * s * .62, ay = y - uy * s + ux * s * .62, bx = x - ux * s + uy * s * .62, by = y - uy * s - ux * s * .62;
      return `M${f(ax)} ${f(ay)}L${f(x)} ${f(y)}L${f(bx)} ${f(by)}`;
    };
    root.querySelectorAll("[data-to]").forEach(a => {
      const ra = a.getBoundingClientRect();
      for (const id of a.dataset.to.split(/\s+/)) {
        const b = id && document.getElementById(id);
        if (!b) continue;
        const rb = b.getBoundingClientRect();
        if (rb.left >= ra.right - 1) {
          // across: right side to left side, a curve with level ends; a fan where several share an end
          const x1 = ra.right - o.left, y1 = ra.top + ra.height / 2 - o.top, x2 = rb.left - o.left - 1, y2 = rb.top + rb.height / 2 - o.top;
          const c = Math.max(18, (x2 - x1) * .5);
          lines += `M${f(x1)} ${f(y1)}C${f(x1 + c)} ${f(y1)} ${f(x2 - c)} ${f(y2)} ${f(x2)} ${f(y2)}`;
          heads += head(x2, y2, 1, 0);
        } else if (rb.top >= ra.bottom - 1) {
          // down: bottom to top, at the middle of the stretch the two share
          const lo = Math.max(ra.left, rb.left), hi = Math.min(ra.right, rb.right);
          const x = (hi > lo ? (lo + hi) / 2 : rb.left + rb.width / 2) - o.left;
          const y1 = ra.bottom - o.top, y2 = rb.top - o.top - 1;
          lines += `M${f(x)} ${f(y1)}L${f(x)} ${f(y2)}`;
          heads += head(x, y2, 0, 1);
        }
      }
    });
    svg.innerHTML = `<path d="${lines}"/><path class="head" d="${heads}"/>`;
  };
  const linked = Array.from(document.querySelectorAll("[data-links]"));
  if (linked.length) {
    linked.forEach(root => root.classList.add("linked"));
    const redraw = () => linked.forEach(draw);
    redraw();
    if ("ResizeObserver" in window) { const ro = new ResizeObserver(redraw); linked.forEach(r => ro.observe(r)); }
    else window.addEventListener("resize", redraw);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(redraw);
    window.addEventListener("load", redraw);
  }

  // the gate's early diamond rings once it has landed: when its row is well inside the window (the travel itself is
  // scroll-driven in site.css, and ends a little before this line)
  const early = document.querySelector(".mark.early");
  if (early && !reduce && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(entries => {
      for (const e of entries) if (e.isIntersecting) { early.classList.add("landed"); io.disconnect(); }
    }, { rootMargin: "0px 0px -42% 0px" });
    io.observe(early);
  }
})();
