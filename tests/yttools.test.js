// Run: node tests/yttools.test.js
const assert = require("node:assert/strict");
const Y = require("../assets/yttools.js");
let r = Y.checkTitle("GTA 6 باعت 32.5 مليون نسخة قبل لا تنزل!", "قبل الإطلاق");
assert.ok(r.good.some(g => g.includes("32.5")), "number detected");
assert.ok(!r.issues.some(i => i[0] === "duplicate"));
r = Y.checkTitle("شي مذهل وخطير صار", "شي مذهل");
assert.ok(r.issues.some(i => i[0] === "vague")); assert.ok(r.issues.some(i => i[0] === "duplicate")); assert.ok(r.issues.some(i => i[0] === "no-number"));
r = Y.checkTitle("ا".repeat(70)); assert.ok(r.issues.some(i => i[0] === "length")); assert.ok(r.issues.some(i => i[0] === "mobile"));
assert.equal(Y.checkTitle("").score, 0);
assert.ok(Y.checkTitle("ليش ٣ دول؟").good.some(g => g.includes("سؤال")), "Arabic question mark");
assert.ok(Y.checkTitle("كم عددها ٣٢ ؟").good.some(g => g.includes("32")), "Arabic digits");
// subtitles + chapters
let srt = ""; const topics = ["اللؤلؤ الغوص البحر السفينة", "النفط الشركة الحفر البئر", "البنك الدينار العملة الاقتصاد", "الكورة الدوري النادي البطولة"];
let t = 0, n = 1; const f = x => { const ms = Math.round((x % 1) * 1000); return `00:${Y.mmss(x)},${String(ms).padStart(3, "0")}`; };
topics.forEach((tp, k) => { for (let j = 0; j < 6; j++) { const s = t, e = t + 4; srt += `${n++}\n${f(s)} --> ${f(e)}\n${tp} كلام رقم ${j}\n\n`; t = e + (j === 5 ? 3 : 0.2); } });
const cues = Y.parseSubs(srt); assert.equal(cues.length, 24); assert.equal(cues[1][0], 4.2);
const ch = Y.chapters(cues, 4); assert.equal(ch.valid, true, JSON.stringify(ch)); assert.equal(ch.chapters[0].label, "00:00");
assert.equal(ch.chapters.length, 4); assert.ok(ch.chapters[1].draft.includes("النفط") || ch.chapters[1].draft.length > 0);
assert.equal(Y.chapters(cues.slice(0, 3)).valid, false);
assert.ok(Y.chapters(Y.parseSubs(srt.replace(/الشركه|الشركة/g, "الشركة")), 4).chapters.some(c => c.draft.includes("الشركة")), "original spelling kept");
assert.equal(Y.parseSubs("WEBVTT\n\n00:00:01.000 --> 00:00:02.500 align:start\n<v A>هلا</v>\n").length, 1);
// retention
let csv = "Video position (%),Audience retention (%)\n"; for (let i = 0; i <= 100; i += 5) csv += `${i},${i === 0 ? 100 : i <= 10 ? 70 : i === 50 ? 40 : 60 - i * 0.1}\n`;
const rt = Y.retention(csv, 120, cues);
assert.ok(rt.hookLeak >= 30, "hook leak"); assert.equal(rt.hookLeak, 42.5); assert.equal(rt.verdict, "تسريب قوي"); assert.ok(rt.cliffs.some(c => c.seconds === 54 && c.said.length > 0), "mid cliff at 54s with transcript"); assert.ok(rt.cliffs.length >= 1);
assert.ok(Y.retention("a,b\n1,2").error);
console.log("yttools: all checks passed");
