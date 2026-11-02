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
    const io = new IntersectionObserver(entries => {
      for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.08 });
    items.forEach(el => io.observe(el));
    // if the observer is slow (a background tab, a print preview), what is already on screen shows anyway;
    // what is below the fold still waits to be scrolled to
    const inView = el => el.getBoundingClientRect().top < window.innerHeight;
    setTimeout(() => items.forEach(el => { if (inView(el)) el.classList.add("in"); }), 1500);
    window.addEventListener("beforeprint", () => items.forEach(el => el.classList.add("in")));
  } else items.forEach(el => el.classList.add("in"));

  // the counter in the hero's foot follows the numbered section the reader is in
  const counter = document.querySelector(".hero-foot .counter");
  const secs = Array.from(document.querySelectorAll("main .sec[data-n]"));
  if (counter && secs.length && "IntersectionObserver" in window) {
    const total = String(secs.length).padStart(2, "0");
    const io = new IntersectionObserver(entries => {
      for (const e of entries) if (e.isIntersecting) counter.innerHTML = `<b>${e.target.dataset.n}</b> / ${total}`;
    }, { rootMargin: "-40% 0px -50% 0px" });
    secs.forEach(s => io.observe(s));
  }
})();
