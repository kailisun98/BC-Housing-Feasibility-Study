/* First Read, the home page. The page reads without script; this only marks, in the top bar, the section the
   reader is in, so a long page can be browsed by its four anchors. Nothing here calculates a rule. */

(() => {
  const links = Array.from(document.querySelectorAll(".topnav a[href^='#']"));
  const sections = links.map(a => document.querySelector(a.getAttribute("href"))).filter(Boolean);
  if (!links.length || !sections.length || !("IntersectionObserver" in window)) return;

  const mark = id => links.forEach(a => {
    if (a.getAttribute("href") === `#${id}`) a.setAttribute("aria-current", "location");
    else a.removeAttribute("aria-current");
  });

  // a section counts as the reader's once its top passes a line a third of the way down the window; the last one is
  // short, so at the foot of the page it is the reader's whether or not it reached the line
  const seen = new Map();
  const atFoot = () => window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
  const update = () => {
    if (atFoot()) return mark(sections[sections.length - 1].id);
    const current = sections.filter(s => seen.get(s.id)).pop();
    if (current) mark(current.id);
    else if (window.scrollY < sections[0].offsetTop - window.innerHeight / 3) mark("");
  };
  const io = new IntersectionObserver(entries => {
    for (const e of entries) seen.set(e.target.id, e.isIntersecting);
    update();
  }, { rootMargin: "0px 0px -66% 0px" });
  sections.forEach(s => io.observe(s));
  let frame = 0;
  window.addEventListener("scroll", () => { if (!frame) frame = requestAnimationFrame(() => { frame = 0; update(); }); }, { passive: true });
})();
