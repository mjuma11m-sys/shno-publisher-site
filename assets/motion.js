/* Salfa Studio motion layer (DW-142). No libraries. Skips everything when the user prefers reduced motion. */
(function(){
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hdr = document.querySelector("header.top");
  var bar = document.createElement("div"); bar.className = "progress"; bar.setAttribute("aria-hidden", "true");
  if (!reduce) document.body.appendChild(bar);
  var ticking = false;
  function onScroll(){ if (ticking) return; ticking = true; requestAnimationFrame(function(){
    var h = document.documentElement, max = h.scrollHeight - h.clientHeight;
    if (hdr) hdr.classList.toggle("scrolled", h.scrollTop > 8);
    if (!reduce) bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, h.scrollTop / max) : 0) + ")";
    ticking = false; }); }
  addEventListener("scroll", onScroll, {passive: true}); onScroll();
  // cursor glow on cards
  document.addEventListener("pointermove", function(e){
    var c = e.target.closest && e.target.closest(".card,.lc"); if (!c) return;
    var r = c.getBoundingClientRect(); c.style.setProperty("--mx", (e.clientX - r.left) + "px"); c.style.setProperty("--my", (e.clientY - r.top) + "px");
  }, {passive: true});
  if (reduce || !("IntersectionObserver" in window)) return;
  // reveal on scroll (content is visible without JS; the class is only added here)
  var sel = "main section > h2, main .card, main .lc, main details, main .hk > div, main .sbox, main article section, main .ways li, main .steps li";
  var els = Array.prototype.slice.call(document.querySelectorAll(sel)).filter(function(el){ return el.getBoundingClientRect().top > innerHeight * 0.9; });
  if (!els.length) return;
  document.documentElement.classList.add("mo");
  els.forEach(function(el, i){ el.classList.add("rv"); el.style.setProperty("--d", ((i % 4) * 0.07) + "s"); });
  // reveal anything that has reached (or passed) the lower part of the screen; also covers jumps and fast scrolls
  var pending = els.slice();
  function reveal(){ if (!pending.length) return; var lim = innerHeight * 0.92;
    pending = pending.filter(function(el){ if (el.getBoundingClientRect().top < lim){ el.classList.add("in"); return false; } return true; }); }
  addEventListener("scroll", function(){ requestAnimationFrame(reveal); }, {passive: true}); addEventListener("resize", reveal); reveal();
  // count-up for the stat strip
  var nums = document.querySelectorAll(".hk b");
  var cio = new IntersectionObserver(function(es){ es.forEach(function(en){ if (!en.isIntersecting) return; cio.unobserve(en.target);
    var el = en.target, txt = el.textContent, n = parseInt(txt.replace(/[^\d]/g, ""), 10); if (!n || n < 10) return;
    var t0 = performance.now(), dur = 1100; (function step(t){ var p = Math.min(1, (t - t0) / dur), v = Math.round(n * (1 - Math.pow(1 - p, 3)));
      el.textContent = v.toLocaleString("en-US"); if (p < 1) requestAnimationFrame(step); else el.textContent = txt; })(t0); }); }, {threshold: .6});
  Array.prototype.forEach.call(nums, function(b){ cio.observe(b); });
})();
