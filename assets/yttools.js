/* Salfa Studio YouTube tools: title check, chapters from subtitles, retention leaks.
   Ported to the browser and adapted for Arabic from jakeschincariol/youtube-agent-skill (MIT License,
   Copyright (c) 2026 Jake Schincariol): yt-package/title.py, yt-chapters/chapters.py, yt-retention/retention.py.
   Everything runs in the page; nothing is uploaded. */
(function (root) {
  "use strict";
  var DESKTOP = 60, MOBILE = 40, HARD = 100, MIN_CH = 10;
  var AR_DIAC = /[ً-ٰٟـ]/g;
  function norm(s) {
    return String(s || "").toLowerCase().replace(AR_DIAC, "")
      .replace(/[إأآٱ]/g, "ا").replace(/ى/g, "ي").replace(/ة/g, "ه")
      .replace(/[٠-٩]/g, function (d) { return String(d.charCodeAt(0) - 0x660); });
  }
  function words(t) { return norm(t).match(/[a-z0-9'ء-ي]+/g) || []; }
  var STOP = new Set(("the a an of for to in on and or is are with your you my i this that it how what why " +
    "في من على عن الى الي مع و او ثم هذا هذي هذه هالـ ذا اللي الذي التي هو هي انت انا احنا كان كانت يكون " +
    "شنو ليش شلون كيف متى وين مو ما لا بس عشان لين قد كل بعد قبل يعني").split(" ").map(norm));
  var VAGUE = new Set(("amazing incredible insane crazy huge massive ultimate best powerful secret revolutionary " +
    "epic perfect complete everything مذهل مذهله صادم صادمه خطير خطيره جنوني جنونيه رهيب رهيبه " +
    "اقوي افضل اخطر سر اسرار مستحيل لن تصدق خرافي خرافيه").split(" ").map(norm));

  function checkTitle(title, thumb) {
    var t = String(title || "").trim(), n = [...t].length, issues = [], good = [];
    if (!n) return { title: t, chars: 0, score: 0, issues: [["empty", "اكتب عنوان"]], good: [] };
    if (n > HARD) issues.push(["length", n + " حرف، والحد الأقصى بيوتيوب " + HARD]);
    else if (n > DESKTOP) issues.push(["length", n + " حرف، بحث الكمبيوتر يقص عند حوالي " + DESKTOP]);
    else good.push(n + " حرف، داخل حد الكمبيوتر (" + DESKTOP + ")");
    if (n > MOBILE) {
      var head = [...t].slice(0, MOBILE).join(""), sp = head.lastIndexOf(" ");
      issues.push(["mobile", "الجوال يبين تقريباً «" + (sp > 0 ? head.slice(0, sp) : head) + "…»، تأكد الموضوع باين"]);
    }
    var caps = t.split(/\s+/).filter(function (w) { return w.length > 2 && /[A-Z]/.test(w) && w === w.toUpperCase(); });
    if (caps.length > 2) issues.push(["shouting", caps.length + " كلمات إنقليزية كلها كابيتال، أكثر من ثنتين تبين سبام"]);
    var tw = words(t), v = tw.filter(function (w) { return VAGUE.has(w); });
    if (v.length) issues.push(["vague", "«" + Array.from(new Set(v)).join("، ") + "» كلام عام، بدّله برقم أو اسم أو تاريخ"]);
    var nums = norm(t).match(/\d[\d,.]*%?/g);
    if (nums) good.push("فيه رقم واضح (" + nums.slice(0, 3).join("، ") + ")");
    else issues.push(["no-number", "ما فيه رقم ولا تاريخ ولا اسم، هذا أسهل تحسين"]);
    if (/[?؟]\s*$/.test(t)) good.push("العنوان سؤال مفتوح");
    if (!tw.slice(0, 3).some(function (w) { return !STOP.has(w); })) issues.push(["front-load", "أول ثلاث كلمات كلها حشو، قدّم الموضوع"]);
    if (thumb && String(thumb).trim()) {
      var a = new Set(tw.filter(function (w) { return !STOP.has(w); }));
      var hw = words(thumb).filter(function (w) { return !STOP.has(w); });
      var shared = Array.from(new Set(hw.filter(function (w) { return a.has(w); })));
      if (shared.length) issues.push(["duplicate", "الكفر يكرر العنوان («" + shared.join("، ") + "»)، خل الكفر يقول شي ما قاله العنوان"]);
      else good.push("الكفر والعنوان كل واحد يقول شي مختلف");
      if (words(thumb).length > 4) issues.push(["thumb-length", words(thumb).length + " كلمات على الكفر، الحد ثلاث كلمات بحجم الفيد"]);
    }
    var score = Math.max(0, Math.min(100, 100 - 14 * issues.length + 4 * good.length));
    return { title: t, chars: n, score: score, issues: issues, good: good };
  }

  function ts(s) {
    var m = String(s).trim().replace(",", ".").split(":").map(Number);
    if (m.some(isNaN)) return NaN;
    return m.length === 3 ? m[0] * 3600 + m[1] * 60 + m[2] : m.length === 2 ? m[0] * 60 + m[1] : m[0];
  }
  // SRT or VTT text -> [[start, end, text], ...]
  function parseSubs(raw) {
    var out = [], blocks = String(raw || "").replace(/\r/g, "").split(/\n\s*\n/);
    blocks.forEach(function (b) {
      var lines = b.split("\n"), i = lines.findIndex(function (l) { return l.indexOf("-->") > -1; });
      if (i < 0) return;
      var p = lines[i].split("-->"), s = ts(p[0]), e = ts(String(p[1]).trim().split(/\s+/)[0]);
      var text = lines.slice(i + 1).join(" ").replace(/<[^>]+>/g, "").trim();
      if (!isNaN(s) && !isNaN(e) && text) out.push([s, e, text]);
    });
    return out;
  }
  function keywords(text) {
    return new Set(words(text).filter(function (w) { return w.length >= 4 && !STOP.has(w) && !/^\d+$/.test(w); }));
  }
  function mmss(t) {
    t = Math.floor(t); var h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = t % 60;
    var p = function (x) { return (x < 10 ? "0" : "") + x; };
    return h ? h + ":" + p(m) + ":" + p(s) : p(m) + ":" + p(s);
  }
  function chapters(cues, target) {
    target = target || 7;
    if (cues.length < 6) return { valid: false, error: "الترجمة قصيرة، تحتاج 6 أسطر على الأقل", chapters: [] };
    var dur = cues[cues.length - 1][1], cand = [];
    for (var i = 1; i < cues.length; i++) {
      var gap = cues[i][0] - cues[i - 1][1];
      var kb = keywords(cues.slice(Math.max(0, i - 12), i).map(function (c) { return c[2]; }).join(" "));
      var ka = keywords(cues.slice(i, i + 12).map(function (c) { return c[2]; }).join(" "));
      var uni = new Set([...kb, ...ka]), inter = [...kb].filter(function (w) { return ka.has(w); }).length;
      var shift = uni.size ? 1 - inter / uni.size : 0;
      cand.push([gap * 1.6 + shift * 3.2, cues[i][0]]);
    }
    cand.sort(function (a, b) { return b[0] - a[0]; });
    var picked = [0];
    for (var k = 0; k < cand.length && picked.length < target; k++) {
      var t = cand[k][1];
      if (picked.every(function (p) { return Math.abs(t - p) >= MIN_CH; }) && dur - t >= MIN_CH) picked.push(t);
    }
    picked.sort(function (a, b) { return a - b; });
    var list = picked.map(function (t, n) {
      var end = n + 1 < picked.length ? picked[n + 1] : dur;
      var text = cues.filter(function (c) { return c[0] >= t && c[1] <= end; }).map(function (c) { return c[2]; }).join(" ");
      var low = norm(text), kw = Array.from(keywords(text));
      kw.sort(function (a, b) { return low.split(b).length - low.split(a).length; });
      var orig = {};
      (String(text).toLowerCase().match(/[a-z0-9'\u0621-\u0652]+/g) || []).forEach(function (w) { var k = norm(w); if (!orig[k]) orig[k] = w; });
      return { start: t, label: mmss(t), draft: kw.slice(0, 3).map(function (w) { return orig[w] || w; }).join(" ") || "قسم", seconds: end - t };
    });
    var ok = list.length >= 3 && list[0].start === 0 && list.every(function (c) { return c.seconds >= MIN_CH; });
    return { valid: ok, chapters: list };
  }

  // YouTube Studio "Audience retention" CSV -> hook leak, cliffs, slide
  function retention(raw, duration, cues) {
    var rows = [];
    String(raw || "").replace(/\r/g, "").split("\n").forEach(function (line) {
      var vals = line.split(/[,;\t]/).map(function (c) { return parseFloat(c.replace(/["%\s]/g, "")); })
        .filter(function (x) { return !isNaN(x); });
      if (vals.length >= 2) rows.push([vals[0], vals[1]]);
    });
    if (rows.length < 8) return { error: "ما قدرت أقرا 8 نقاط على الأقل من الملف" };
    var xs = rows.map(function (r) { return r[0]; }), ys = rows.map(function (r) { return r[1]; });
    var pct = Math.max.apply(null, xs) <= 100.5, dur = duration > 0 ? duration : null;
    var at = function (x) { return pct && dur ? x / 100 * dur : (pct ? null : x); };
    var start = ys[0] || 100, cutoff = !pct ? 30 : (dur ? 30 / dur * 100 : 10);
    var hookEnd = rows.filter(function (r) { return r[0] <= cutoff; }).map(function (r) { return r[1]; });
    var leak = start - (hookEnd.length ? Math.min.apply(null, hookEnd) : start);
    var drops = [];
    for (var i = 1; i < rows.length; i++) {
      var d = ys[i - 1] - ys[i], span = (xs[i] - xs[i - 1]) || 1;
      drops.push({ rate: d / span, from: xs[i - 1], to: xs[i], lost: d });
    }
    var mid = drops.filter(function (d) { return d.from > cutoff; }).map(function (d) { return d.rate; });
    var slide = mid.length ? mid.reduce(function (a, b) { return a + b; }, 0) / mid.length : 0;
    var cliffs = drops.slice().sort(function (a, b) { return b.rate - a.rate; }).slice(0, 5)
      .filter(function (d) { return d.lost > 0.8; })
      .map(function (d) {
        var s = at(d.from), said = "";
        if (cues && s !== null) said = cues.filter(function (q) { return q[0] <= s + 4 && q[1] >= s - 4; }).map(function (q) { return q[2]; }).join(" ").slice(0, 140);
        return { from: d.from, lost: +d.lost.toFixed(2), seconds: s, said: said };
      });
    return { points: rows.length, start: start, end: ys[ys.length - 1], hookLeak: +leak.toFixed(2),
      verdict: leak < 25 ? "سليم" : leak < 40 ? "فيه تسريب" : "تسريب قوي", cliffs: cliffs, slide: +slide.toFixed(3), pctAxis: pct };
  }

  var api = { checkTitle: checkTitle, parseSubs: parseSubs, chapters: chapters, retention: retention, mmss: mmss, norm: norm };
  if (typeof module === "object" && module.exports) module.exports = api; else root.YTT = api;
})(this);
