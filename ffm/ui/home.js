/* Funding-Fit Memo, the home page: the ruler's switch, which moves the six findings from the weeks they
   usually arrive in to day one, and the as-of switch in the rule-change section. Nothing here calculates a
   rule; every figure on the page is copied from the committed 998 E 19th Ave runs. */

(() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
  const EASE = "cubic-bezier(.2, .7, .2, 1)";
  const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wide = () => window.matchMedia("(min-width: 900px)").matches;

  // ---------------------------------------------------------------- the ruler

  const ruler = $("#ruler");

  // In the late state each finding hangs from its week in one of two lanes; a lane is as tall as its tallest note.
  function measureLanes() {
    if (!ruler) return;
    if (ruler.dataset.state !== "late" || !wide()) {
      ruler.style.removeProperty("--lane1");
      ruler.style.removeProperty("--lane2");
      return;
    }
    const tallest = [0, 0];
    for (const pin of $$(".pin", ruler)) {
      const lane = Number(pin.dataset.lane) - 1;
      tallest[lane] = Math.max(tallest[lane], pin.offsetHeight);
    }
    ruler.style.setProperty("--lane1", `${tallest[0]}px`);
    ruler.style.setProperty("--lane2", `${tallest[1]}px`);
  }

  // FLIP: note where each finding is, change the state, measure again, and play the difference back.
  function setRuler(next) {
    if (!ruler || ruler.dataset.state === next) return;
    const pins = $$(".pin", ruler);
    const box = $(".pins", ruler);
    const first = pins.map(p => p.getBoundingClientRect());
    const h0 = box.getBoundingClientRect().height;

    ruler.dataset.state = next;
    $$(".switch button", ruler).forEach(b => b.setAttribute("aria-pressed", String(b.dataset.state === next)));
    measureLanes();
    if (reduced()) return;

    const h1 = box.getBoundingClientRect().height;
    if (h0 !== h1) box.animate([{ height: `${h0}px` }, { height: `${h1}px` }], { duration: 420, easing: EASE });
    pins.forEach((pin, i) => {
      const last = pin.getBoundingClientRect();
      const dx = first[i].left - last.left;
      const dy = first[i].top - last.top;
      if (!dx && !dy) return;
      pin.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }],
        { duration: 420 + i * 30, easing: EASE });
    });
  }

  if (ruler) {
    $$(".switch button", ruler).forEach(b => b.addEventListener("click", () => setRuler(b.dataset.state)));
    let frame = 0;
    window.addEventListener("resize", () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measureLanes);
    });
    measureLanes();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(measureLanes);

    // on paper the findings carry their statuses and owners: print the day-one state, then put the switch back
    let before = null;
    window.addEventListener("beforeprint", () => {
      before = ruler.dataset.state;
      ruler.dataset.state = "day1";
      measureLanes();
    });
    window.addEventListener("afterprint", () => {
      if (before) ruler.dataset.state = before;
      before = null;
      measureLanes();
    });
  }

  // ---------------------------------------------------------------- the rule change

  const change = $("#change-view");
  if (change) {
    const body = $(".change-body", change);
    $$(".switch button", change).forEach(b => b.addEventListener("click", () => {
      if (change.dataset.asof === b.dataset.asof) return;
      change.dataset.asof = b.dataset.asof;
      $$(".switch button", change).forEach(x => x.setAttribute("aria-pressed", String(x === b)));
      if (!reduced()) body.animate([{ opacity: 0.25 }, { opacity: 1 }], { duration: 160, easing: "ease-out" });
    }));
  }
})();
