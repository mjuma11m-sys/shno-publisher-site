"""Episode pages for the long «شنو السالفة؟» videos.

  python3 tools/build_episodes.py --fetch   # pull long videos from YouTube Data API into data/episodes.json, then build
  python3 tools/build_episodes.py           # build episodes.html + episode-<id>.html from data/episodes.json

The API key is injected by the network proxy (header x-goog-api-key); nothing secret lives here.
"""
import html, json, os, re, sys, urllib.parse, urllib.request
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = "https://salfa-studio.vercel.app/"
API = "https://youtube.googleapis.com/youtube/v3/"


def get(path):
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.load(r)


def iso_secs(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d)
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1)))


def fetch():
    ch = get("channels?part=contentDetails&forHandle=shnoalsalfa_bh")["items"][0]
    up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], ""
    while True:
        r = get(f"playlistItems?part=contentDetails&maxResults=50&playlistId={up}" + (f"&pageToken={tok}" if tok else ""))
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            break
    eps, shorts = [], []
    for k in range(0, len(ids), 50):
        for v in get("videos?part=snippet,contentDetails,statistics,status&id=" + ",".join(ids[k:k + 50]))["items"]:
            secs = iso_secs(v["contentDetails"]["duration"])
            if v["status"]["privacyStatus"] != "public":
                continue
            s = v["snippet"]
            if secs < 180:
                shorts.append({"id": v["id"], "title": re.sub(r"\s#\S+", "", s["title"]).strip(), "published": s["publishedAt"],
                               "duration": v["contentDetails"]["duration"], "description": s["description"],
                               "thumb": next(s["thumbnails"][k]["url"] for k in ("high", "medium", "default") if k in s["thumbnails"])})
                continue
            eps.append({"id": v["id"], "title": s["title"], "published": s["publishedAt"], "duration": v["contentDetails"]["duration"],
                        "secs": secs, "thumb": next(s["thumbnails"][k]["url"] for k in ("maxres", "standard", "high", "medium", "default") if k in s["thumbnails"]),
                        "description": s["description"]})
    eps.sort(key=lambda e: e["published"], reverse=True)
    shorts.sort(key=lambda e: e["published"], reverse=True)
    json.dump(eps, open("data/episodes.json", "w"), ensure_ascii=False, indent=1)
    json.dump(shorts, open("data/shorts.json", "w"), ensure_ascii=False, indent=1)
    print("fetched", len(eps), "long episodes,", len(shorts), "shorts")


CREDIT = ("📚", "📷", "🛰", "🎞", "🗺", "🎙", "🎵", "🪙", "💵", "⚠")


def parse(desc):
    lines = [l.strip() for l in desc.splitlines()]
    summary = lines[0] if lines else ""
    chapters = []
    for l in lines:
        m = re.match(r"^(?:(\d+):)?(\d+):(\d\d)\s+(.+)$", l)
        if m:
            h, mi, se, t = m.groups()
            chapters.append({"t": int(h or 0) * 3600 + int(mi) * 60 + int(se), "label": l.split(" ", 1)[0], "title": t})
    credits = [l for l in lines if l.startswith(CREDIT)]
    tags = re.findall(r"#(\S+)", desc)
    return summary, chapters, credits, tags


TOPICS = {"GTA والألعاب": ["gta", "minecraft", "روكستار"], "إيران والخليج": ["إيران", "هرمز", "ايران"], "الموناليزا": ["الموناليزا", "بيكاسو", "اللوفر"],
          "اقتصاد": ["دينار", "ضريبة", "دولار", "ألمنيوم", "الألمنيوم"], "تاريخ البحرين": ["البحرين", "المنامة", "اللؤلؤ", "نفط", "هولمز", "الغواص"]}


TOPIC_PAGES = {
    "GTA والألعاب": ("gta", "GTA والألعاب", "قصة سلسلة GTA وأرقامها: المبيعات، الكلفة، التأجيلات، وعلاقة الخليج بصناعة الألعاب."),
    "إيران والخليج": ("iran-gulf", "إيران والخليج", "السالفة بين إيران وأمريكا والخليج: من 1953 لين مضيق هرمز والمفاوضات."),
    "الموناليزا": ("mona-lisa", "الموناليزا", "سرقة الموناليزا سنة 1911 وكل اللي صار للوحة قبلها وبعدها."),
    "اقتصاد": ("economy", "اقتصاد وفلوس", "ليش الدينار البحريني غالي، وشلون يشتغل الربط بالدولار، وسوالف الاقتصاد الخليجي."),
    "تاريخ البحرين": ("bahrain-history", "تاريخ البحرين", "من الغوص على اللؤلؤ لأول بير نفط بالخليج: قصص البحرين اللي غيّرت المنطقة."),
}


def topic(t):
    t = t.lower()
    return next((k for k, w in TOPICS.items() if any(x in t for x in w)), "أخرى")


def transcript(vid, chapters):
    """Chapter-grouped paragraphs from data/transcripts/<id>.srt, or [] if none."""
    path = f"data/transcripts/{vid}.srt"
    if not os.path.exists(path):
        return []
    return parse_srt(path, chapters)


def adopt_pending(eps):
    """Move a waiting transcript (data/transcripts/pending/) to <videoId>.srt once its episode is public."""
    cfg = "data/transcripts/pending.json"
    if not os.path.exists(cfg):
        return
    pend = json.load(open(cfg))
    for e in eps:
        for key, fn in list(pend.items()):
            src = f"data/transcripts/pending/{fn}"
            if key in e["title"] and os.path.exists(src) and not os.path.exists(f"data/transcripts/{e['id']}.srt"):
                os.replace(src, f"data/transcripts/{e['id']}.srt")
                del pend[key]
                print("transcript adopted:", e["title"])
    json.dump(pend, open(cfg, "w"), ensure_ascii=False)


def parse_srt(path, chapters):
    cues = []
    for block in re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().strip()):
        lines = block.strip().splitlines()
        m = next((re.match(r"(\d+):(\d+):(\d+)", l) for l in lines if "-->" in l), None)
        if m:
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
            text = " ".join(l for l in lines if "-->" not in l and not l.strip().isdigit()).strip()
            if text:
                cues.append((t, text))
    marks = chapters or [{"t": 0, "title": ""}]
    out = []
    for i, c in enumerate(marks):
        end = marks[i + 1]["t"] if i + 1 < len(marks) else 10 ** 9
        words = " ".join(x for t, x in cues if c["t"] <= t < end)
        if words:
            out.append({"t": c["t"], "title": c["title"], "text": words})
    return out


def graph(main, crumbs):
    """JSON-LD @graph: the page's main object plus a BreadcrumbList."""
    m = {k: v for k, v in main.items() if k != "@context"}
    bl = {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)]}
    return {"@context": "https://schema.org", "@graph": [m, bl]}


def linkify(text):
    """Escape, then turn only URLs that are literally in the text into links (never invent one)."""
    out, last = [], 0
    for m in re.finditer(r"https?://[^\s<>«»\"']+[^\s<>«»\"'.,؛،)]", text):
        out.append(html.escape(text[last:m.start()]))
        u = m.group(0)
        out.append(f'<a href="{html.escape(u, quote=True)}" rel="noopener nofollow" target="_blank">{html.escape(u)}</a>')
        last = m.end()
    out.append(html.escape(text[last:]))
    return "".join(out)


def mmss(s):
    return f"{s // 60}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


sys.path.insert(0, "tools")
from shell import page


CSS = """<style>
.ep{padding-block:28px 8px;display:grid;gap:20px}
.crumb{color:var(--mut);font-size:.88rem}.crumb a{color:var(--mut)}
.ep h1{margin:0;font:900 clamp(1.5rem,3.2vw,2.3rem)/1.3 "Tajawal",sans-serif;text-wrap:balance}
.meta{display:flex;gap:8px;flex-wrap:wrap;color:var(--mut);font-size:.88rem}.meta a{color:var(--fg);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:4px 12px;background:var(--bg2)}.meta a:hover{color:var(--ac)}.meta span{border:1px solid var(--line);border-radius:999px;padding:4px 12px;background:var(--bg2)}
.poster{position:relative;display:block;border-radius:20px;overflow:hidden;border:1px solid var(--line);aspect-ratio:16/9;max-width:100%;background:var(--bg2)}
.poster img{width:100%;height:100%;object-fit:cover;display:block}
.poster span{position:absolute;inset-inline-start:16px;bottom:16px;background:#d92b2b;color:#fff;font-weight:800;padding:10px 18px;border-radius:999px}
.ecols{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:20px}
.box{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:18px 20px;min-width:0}
.box h2{margin:0 0 10px;font-size:1.1rem}
.lead{font-size:1.05rem;line-height:1.9;max-width:65ch;margin:0}
.chap{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.chap a{display:grid;grid-template-columns:64px 1fr;gap:10px;padding:8px 4px;border-bottom:1px solid var(--line);color:var(--fg);text-decoration:none}
.chap a:hover{color:var(--ac)}.chap b{font-variant-numeric:tabular-nums;color:var(--ac);direction:ltr;text-align:right;font-weight:700}
.cred{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px;font-size:.9rem;color:var(--mut);line-height:1.7}
.tags{display:flex;gap:6px;flex-wrap:wrap}.tags span{font-size:.8rem;border:1px solid var(--line);border-radius:999px;padding:3px 10px;color:var(--mut)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
.card3{background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;color:var(--fg);text-decoration:none;display:flex;flex-direction:column}
.card3 img{aspect-ratio:16/9;width:100%;object-fit:cover;display:block;background:var(--bg2)}
.card3 div{padding:12px 14px;display:grid;gap:6px}.card3 b{line-height:1.5}.card3 small{color:var(--mut)}
.card3:hover b{color:var(--ac)}
.topics{display:flex;gap:8px;flex-wrap:wrap}.topics a{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:7px 14px;color:var(--fg);text-decoration:none}.topics a:hover{color:var(--ac)}.topics small{color:var(--mut)}
.pn{display:grid;grid-template-columns:1fr 1fr;gap:14px}.pn a{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 16px;color:var(--fg);text-decoration:none;display:grid;gap:2px;line-height:1.5}.pn a:hover{color:var(--ac)}.pn a.old{text-align:left}.pn small{color:var(--mut)}
@media (max-width:600px){.pn{grid-template-columns:1fr}.pn a.old{text-align:right}}
.tk{margin:0;padding:0;list-style:none;counter-reset:k;display:grid;gap:10px}.tk li{counter-increment:k;display:grid;grid-template-columns:32px 1fr;gap:10px;align-items:start;line-height:1.8}
.tk li::before{content:counter(k);width:32px;height:32px;border-radius:50%;background:var(--ac);color:#1a1300;font:900 1rem/32px "Tajawal",sans-serif;text-align:center}
.card3 small{color:var(--mut)}
.share{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.share a,.share button{all:unset;cursor:pointer;border:1px solid var(--line);background:var(--card);border-radius:999px;padding:7px 14px;color:var(--fg)}.share a:hover,.share button:hover{color:var(--ac)}.share a:focus-visible,.share button:focus-visible{outline:2px solid var(--ac);outline-offset:2px}.share input{width:min(100%,360px);font:inherit;padding:6px 10px;border-radius:10px;border:1px solid var(--line);background:var(--bg2);color:var(--fg)}.cpm{color:var(--mut);font-size:.85rem}
.pwrap{display:grid;gap:6px}.pnote{margin:0;color:var(--mut);font-size:.8rem}.pnote a{color:var(--mut)}iframe.poster{width:100%;height:auto}iframe.sh{width:100%;height:auto}
.cta{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;background:var(--card);border:1px dashed var(--ac);border-radius:16px;padding:14px 18px;color:var(--fg);text-decoration:none}.cta span{color:var(--ac)}.cta:hover b{color:var(--ac)}
.chips{display:flex;gap:6px;flex-wrap:wrap}.chips button{all:unset;cursor:pointer;padding:6px 12px;border-radius:999px;border:1px solid var(--line);color:var(--mut);font-size:.85rem}
.chips button[aria-pressed="true"]{background:var(--ac);color:#1a1300;border-color:var(--ac);font-weight:700}.chips button:focus-visible{outline:2px solid var(--ac);outline-offset:2px}
.sgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.sh{position:relative;border-radius:16px;overflow:hidden;border:1px solid var(--line);background:var(--bg2);aspect-ratio:9/16;display:block;color:#fff;text-decoration:none}
.sh img{width:100%;height:100%;object-fit:cover;display:block}
.sh span{position:absolute;inset:auto 0 0 0;padding:28px 10px 10px;font-size:.85rem;line-height:1.5;font-weight:700;background:linear-gradient(transparent,rgba(0,0,0,.85))}
.tr summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.tr summary::-webkit-details-marker{display:none}
.tr summary h2{margin:0}.tr summary h2::before{content:"▸ ";color:var(--ac)}.tr[open] summary h2::before{content:"▾ "}.tr summary span{color:var(--mut);font-size:.85rem}
.tr section{margin-top:16px}.tr h3{margin:0 0 6px;font-size:1rem}.tr h3 a{color:var(--ac);text-decoration:none;font-variant-numeric:tabular-nums;margin-inline-end:6px}
.tr p{margin:0;line-height:2;max-width:70ch}
@media (max-width:900px){.ecols{grid-template-columns:1fr}}
</style>"""

AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def ardate(iso):
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {AR_MONTHS[int(m) - 1]} {y}"


def build():
    eps = json.load(open("data/episodes.json"))
    adopt_pending(eps)
    takeaways = json.load(open("data/takeaways.json")) if os.path.exists("data/takeaways.json") else {}
    shorts = json.load(open("data/shorts.json")) if os.path.exists("data/shorts.json") else []
    e_ = html.escape
    for i, e in enumerate(eps):
        summary, chapters, credits, tags = parse(e["description"])
        thumb = e.get("thumb") or f"https://i.ytimg.com/vi/{e['id']}/hqdefault.jpg"
        url = f"{BASE}episode-{e['id']}.html"
        watch = f"https://www.youtube.com/watch?v={e['id']}"
        ld = {"@context": "https://schema.org", "@type": "VideoObject", "name": e["title"], "description": summary,
              "thumbnailUrl": [thumb], "uploadDate": e["published"], "duration": e["duration"], "inLanguage": "ar",
              "embedUrl": f"https://www.youtube.com/embed/{e['id']}", "url": url,
              "publisher": {"@type": "Organization", "name": "شنو السالفة؟", "url": BASE},
              "hasPart": [{"@type": "Clip", "name": c["title"], "startOffset": c["t"],
                           "endOffset": (chapters[i + 1]["t"] if i + 1 < len(chapters) else e["secs"]),
                           "url": f"{watch}&t={c['t']}s"} for i, c in enumerate(chapters)]}
        rel = [x for x in shorts if topic(x["title"]) == topic(e["title"]) != "أخرى"][:6]
        rel_html = ("" if not rel else '<section class="box"><h2>شورتس من نفس الموضوع</h2><div class="sgrid">'
                    + "".join(f'<a class="sh" href="short-{x["id"]}.html"><img src="{x["thumb"]}" alt="" loading="lazy" width="480" height="360"><span>{e_(x["title"])}</span></a>' for x in rel) + "</div></section>")
        newer, older = (eps[i - 1] if i > 0 else None), (eps[i + 1] if i + 1 < len(eps) else None)
        pn_html = ('<nav class="pn" aria-label="حلقات ثانية">'
                   + (f'<a href="episode-{newer["id"]}.html" rel="next"><small>الحلقة الأحدث</small>{e_(newer["title"])}</a>' if newer else "<span></span>")
                   + (f'<a href="episode-{older["id"]}.html" rel="prev" class="old"><small>الحلقة الأقدم</small>{e_(older["title"])}</a>' if older else "<span></span>")
                   + "</nav>")
        tr = transcript(e["id"], chapters)
        if tr:
            ld["transcript"] = " ".join(x["text"] for x in tr)
        tr_html = ("" if not tr else '<details class="box tr"><summary><h2>النص الكامل للحلقة</h2><span>من ترجمة الحلقة · ' + str(len(tr)) + ' فصل</span></summary>'
                   + "".join(f'<section><h3><a href="{watch}&amp;t={x["t"]}s" target="_blank" rel="noopener">{mmss(x["t"])}</a> {e_(x["title"])}</h3><p>{e_(x["text"])}</p></section>' for x in tr) + "</details>")
        body = f"""{CSS}<div class="wrap"><article class="ep">
<nav class="crumb" aria-label="مسار الصفحة"><a href="episodes.html">الحلقات</a> ‹ {e_(e['title'][:40])}</nav>
<h1>{e_(e['title'])}</h1>
<div class="meta"><span class="pill">{ardate(e['published'])}</span><span class="pill">{mmss(e['secs'])} دقيقة</span>{f'<a class="pill" href="topic-{TOPIC_PAGES[topic(e["title"])][0]}.html">{TOPIC_PAGES[topic(e["title"])][1]}</a>' if topic(e["title"]) in TOPIC_PAGES else '<span class="pill">باللهجة البحرينية</span>'}</div>
<div class="pwrap"><a class="poster" href="{watch}" target="_blank" rel="noopener" data-yt="{e['id']}"><img src="{thumb}" alt="غلاف حلقة {e_(e['title'])}" loading="eager" width="1280" height="720"><span>▶ شغّل الحلقة هني</span></a><p class="pnote">التشغيل من يوتيوب ويبدأ لما تضغط بس · <a href="{watch}" target="_blank" rel="noopener">أو افتحها على يوتيوب</a></p></div>
<script>document.querySelectorAll(".poster[data-yt]").forEach(a=>a.addEventListener("click",e=>{{if(e.ctrlKey||e.metaKey||e.shiftKey)return;e.preventDefault();const f=document.createElement("iframe");f.src="https://www.youtube-nocookie.com/embed/"+a.dataset.yt+"?autoplay=1&rel=0";f.title=a.querySelector("img").alt;f.allow="autoplay; encrypted-media; picture-in-picture; fullscreen";f.allowFullscreen=true;f.className="poster";f.style.border="0";a.replaceWith(f);f.focus()}}))</script>
<div class="ecols">
 <div style="display:grid;gap:20px;align-content:start">
  <section class="box"><h2>شنو السالفة؟</h2><p class="lead">{e_(summary)}</p></section>
  {('<section class="box"><h2>شنو تعلمنا</h2><ol class="tk">' + "".join(f"<li>{e_(t)}</li>" for t in takeaways[e["id"]]) + "</ol></section>") if e["id"] in takeaways else ""}
  <section class="box"><h2>المصادر والحقوق</h2><ul class="cred">{''.join(f'<li>{linkify(c)}</li>' for c in credits) or '<li>المصادر بوصف الفيديو على يوتيوب.</li>'}</ul></section>
  <div class="tags">{''.join(f'<span>#{e_(t)}</span>' for t in tags)}</div>
 </div>
 <section class="box"><h2>الفصول</h2><ol class="chap">{''.join(f'<li><a href="{watch}&amp;t={c["t"]}s" target="_blank" rel="noopener"><b>{c["label"]}</b><span>{e_(c["title"])}</span></a></li>' for c in chapters)}</ol></section>
</div>
<div class="share" role="group" aria-label="شارك الحلقة"><button type="button" class="cp" data-u="{url}">انسخ الرابط</button><a href="https://wa.me/?text={urllib.parse.quote(e['title'] + ' ' + url)}" target="_blank" rel="noopener">واتساب</a><span class="cpm" role="status" aria-live="polite"></span></div>
{rel_html}
{tr_html}
{pn_html}
<script>document.querySelectorAll(".share .cp").forEach(b=>b.addEventListener("click",async()=>{{const m=b.parentNode.querySelector(".cpm");try{{await navigator.clipboard.writeText(b.dataset.u);m.textContent="انسخ ✓"}}catch(e){{const i=document.createElement("input");i.value=b.dataset.u;b.after(i);i.select();m.textContent="انسخ الرابط من الخانة"}}}}))</script>
</article></div>"""
        title = f"{e['title']} · شنو السالفة؟"
        crumbs = [("الرئيسية", BASE), ("الحلقات", f"{BASE}episodes.html")]
        if topic(e["title"]) in TOPIC_PAGES:
            crumbs.append((TOPIC_PAGES[topic(e["title"])][1], f"{BASE}topic-{TOPIC_PAGES[topic(e['title'])][0]}.html"))
        crumbs.append((e["title"], url))
        page(f"episode-{e['id']}.html", title, summary[:155], body, nav="episodes.html", image=thumb, og_type="video.other", ld=graph(ld, crumbs))
    shorts_html = ""
    if shorts:
        used = [k for k in list(TOPICS) + ["أخرى"] if any(topic(x["title"]) == k for x in shorts)]
        chips = '<button type="button" data-t="" aria-pressed="true">الكل</button>' + "".join(f'<button type="button" data-t="{k}" aria-pressed="false">{k}</button>' for k in used)
        tiles = "".join(f'<a class="sh" data-t="{topic(x["title"])}" href="short-{x["id"]}.html"><img src="{x["thumb"]}" alt="" loading="lazy" width="480" height="360"><span>{e_(x["title"])}</span></a>' for x in shorts)
        shorts_html = (f'<div style="display:grid;gap:12px;margin-top:12px"><h2 style="margin:0;font:900 1.5rem Tajawal,sans-serif">الشورتس <small style="color:var(--mut);font-size:.9rem;font-weight:400">{len(shorts)}</small></h2>'
                       f'<div class="chips" role="group" aria-label="الموضوع">{chips}</div><div class="sgrid">{tiles}</div></div>'
                       '<script>document.querySelectorAll(".chips button").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".chips button").forEach(x=>x.setAttribute("aria-pressed",x===b));document.querySelectorAll(".sh").forEach(a=>a.hidden=!!b.dataset.t&&a.dataset.t!==b.dataset.t)}))</script>')
    cards = "".join(f'<a class="card3" href="episode-{e["id"]}.html"><img src="https://i.ytimg.com/vi/{e["id"]}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180"><div><b>{e_(e["title"])}</b><small>{ardate(e["published"])} · {mmss(e["secs"])} دقيقة</small></div></a>' for e in eps)
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "حلقات شنو السالفة؟",
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}episode-{e['id']}.html"} for i, e in enumerate(eps)]}
    body = f"""{CSS}<div class="wrap"><section class="ep"><div><h1>الحلقات</h1><p style="color:var(--mut);margin:6px 0 0">كل حلقات «شنو السالفة؟» الطويلة: الملخص والفصول ومصادر كل حلقة.</p><p style="margin:6px 0 0;font-size:.95rem"><a href="ideas.html">💡 اقترح موضوع الحلقة الجاية وصوّت ←</a></p><p style="margin:6px 0 0;font-size:.85rem;color:var(--mut)">تابع بـ RSS: <a href="feed.xml">الحلقات</a> · <a href="feed-shorts.xml">الشورتس</a></p></div><div class="grid">{cards}</div>{shorts_html}</section></div>"""
    page("episodes.html", "الحلقات · شنو السالفة؟", "كل حلقات «شنو السالفة؟» باللهجة البحرينية: الحلقات الطويلة بملخصها وفصولها ومصادرها، والشورتس حسب الموضوع.", body, nav="episodes.html", ld=ld)
    # topic hubs
    topic_links = []
    for key, (slug, name, intro) in TOPIC_PAGES.items():
        te = [x for x in eps if topic(x["title"]) == key]
        ts = [x for x in shorts if topic(x["title"]) == key]
        if not te and not ts:
            continue
        topic_links.append(f'<a href="topic-{slug}.html">{name} <small>{len(te) + len(ts)}</small></a>')
        tcards = "".join(f'<a class="card3" href="episode-{x["id"]}.html"><img src="https://i.ytimg.com/vi/{x["id"]}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180"><div><b>{e_(x["title"])}</b><small>{ardate(x["published"])} · {mmss(x["secs"])} دقيقة</small></div></a>' for x in te)
        ttiles = "".join(f'<a class="sh" href="short-{x["id"]}.html"><img src="{x["thumb"]}" alt="" loading="lazy" width="480" height="360"><span>{e_(x["title"])}</span></a>' for x in ts)
        tbody = (f'{CSS}<div class="wrap"><section class="ep"><nav class="crumb" aria-label="مسار الصفحة"><a href="episodes.html">الحلقات</a> ‹ {name}</nav>'
                 f'<div><h1>{name}</h1><p class="lead" style="color:var(--mut);margin-top:6px">{intro}</p></div>'
                 + (f'<h2 style="margin:0;font-size:1.2rem">الحلقات</h2><div class="grid">{tcards}</div>' if te else "")
                 + (f'<h2 style="margin:8px 0 0;font-size:1.2rem">الشورتس</h2><div class="sgrid">{ttiles}</div>' if ts else "")
                 + '</section></div>')
        tld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": f"{name} · شنو السالفة؟", "description": intro,
               "hasPart": [{"@type": "VideoObject", "name": x["title"], "url": f"{BASE}episode-{x['id']}.html"} for x in te]}
        page(f"topic-{slug}.html", f"{name} · شنو السالفة؟", intro, tbody, nav="episodes.html",
             ld=graph(tld, [("الرئيسية", BASE), ("الحلقات", f"{BASE}episodes.html"), (name, f"{BASE}topic-{slug}.html")]))
    if topic_links:
        hub = '<nav class="topics" aria-label="المواضيع">' + "".join(topic_links) + "</nav>"
        txt = open("episodes.html").read().replace('<div class="grid">', hub + '<div class="grid">', 1)
        open("episodes.html", "w").write(txt)
    # per-short pages
    for x in shorts:
        k = topic(x["title"])
        parent = next((y for y in eps if topic(y["title"]) == k), None) if k != "أخرى" else None
        yurl = f"https://www.youtube.com/shorts/{x['id']}"
        desc = (x.get("description") or "").split("\n")[0].strip() or x["title"]
        desc = re.sub(r"\s*#\S+", "", desc).strip() or x["title"]
        sld = {"@context": "https://schema.org", "@type": "VideoObject", "name": x["title"], "description": desc,
               "thumbnailUrl": [x["thumb"]], "uploadDate": x["published"], "inLanguage": "ar", "url": f"{BASE}short-{x['id']}.html",
               "embedUrl": f"https://www.youtube.com/embed/{x['id']}", "publisher": {"@type": "Organization", "name": "شنو السالفة؟", "url": BASE}}
        if x.get("duration"):
            sld["duration"] = x["duration"]
        sb = (f'{CSS}<div class="wrap"><article class="ep" style="max-width:720px">'
              f'<nav class="crumb" aria-label="مسار الصفحة"><a href="episodes.html">الحلقات</a> ‹ شورت</nav>'
              f'<h1>{e_(x["title"])}</h1>'
              f'<div class="meta"><span>{ardate(x["published"])}</span>'
              + (f'<a href="topic-{TOPIC_PAGES[k][0]}.html">{TOPIC_PAGES[k][1]}</a>' if k in TOPIC_PAGES else "") + '</div>'
              f'<div style="display:grid;grid-template-columns:minmax(0,260px) minmax(0,1fr);gap:20px;align-items:start" class="scol">'
              f'<div class="pwrap"><a class="sh" href="{yurl}" target="_blank" rel="noopener" data-yt="{x["id"]}"><img src="{x["thumb"]}" alt="غلاف شورت {e_(x["title"])}" width="480" height="360"><span>▶ شغّل هني</span></a><p class="pnote">التشغيل من يوتيوب ويبدأ لما تضغط · <a href="{yurl}" target="_blank" rel="noopener">أو على يوتيوب</a></p></div>'
              '<script>document.querySelectorAll(".sh[data-yt]").forEach(a=>a.addEventListener("click",e=>{if(e.ctrlKey||e.metaKey||e.shiftKey)return;e.preventDefault();const f=document.createElement("iframe");f.src="https://www.youtube-nocookie.com/embed/"+a.dataset.yt+"?autoplay=1&rel=0";f.title=a.querySelector("img").alt;f.allow="autoplay; encrypted-media; picture-in-picture; fullscreen";f.allowFullscreen=true;f.className="sh";f.style.border="0";a.replaceWith(f);f.focus()}))</script>'
              f'<div style="display:grid;gap:16px"><section class="box"><h2>عن الشورت</h2><p class="lead">{e_(desc)}</p></section>'
              + (f'<a class="card3" href="episode-{parent["id"]}.html"><img src="https://i.ytimg.com/vi/{parent["id"]}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180"><div><small>الحلقة الكاملة</small><b>{e_(parent["title"])}</b></div></a>' if parent else "")
              + '</div></div></article></div><style>@media (max-width:640px){.scol{grid-template-columns:1fr!important}.scol .sh{max-width:260px}}</style>')
        sc = [("الرئيسية", BASE), ("الحلقات", f"{BASE}episodes.html")] + ([(TOPIC_PAGES[k][1], f"{BASE}topic-{TOPIC_PAGES[k][0]}.html")] if k in TOPIC_PAGES else []) + [(x["title"], f"{BASE}short-{x['id']}.html")]
        page(f"short-{x['id']}.html", f"{x['title']} · شنو السالفة؟", desc[:155], sb, nav="episodes.html", image=x["thumb"], og_type="video.other", ld=graph(sld, sc))
    # home page: latest episodes and shorts between <!--LATEST--> markers
    home = open("index.html").read()
    if "<!--LATEST-->" in home:
        lc = "".join(f'<a class="lc" href="episode-{x["id"]}.html"><img src="https://i.ytimg.com/vi/{x["id"]}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180"><b>{e_(x["title"])}</b><small>{ardate(x["published"])} · {mmss(x["secs"])} دقيقة</small></a>' for x in eps[:3])
        ls = "".join(f'<a class="ls" href="short-{x["id"]}.html"><img src="{x["thumb"]}" alt="" loading="lazy" width="480" height="360"><span>{e_(x["title"])}</span></a>' for x in shorts[:4])
        strip = ('<section class="latest"><h2 class="sec">آخر الحلقات</h2><div class="lgrid">' + lc + '</div>'
                 + ('<h3 style="margin:18px 0 10px">آخر الشورتس</h3><div class="sgr">' + ls + '</div>' if ls else "")
                 + '<p style="margin:14px 0 0;display:flex;gap:18px;flex-wrap:wrap"><a href="episodes.html">كل الحلقات والشورتس ←</a><a href="ideas.html">💡 اقترح حلقة وصوّت ←</a></p></section>'
                 '<style>.lgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}'
                 '.lc{display:grid;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:18px;overflow:hidden;color:var(--fg);text-decoration:none;padding-bottom:12px}'
                 '.lc img{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;background:var(--bg2)}.lc b,.lc small{padding-inline:14px;line-height:1.5}.lc small{color:var(--mut)}.lc:hover b{color:var(--ac)}'
                 '.sgr{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.ls{position:relative;display:block;aspect-ratio:9/16;border-radius:16px;overflow:hidden;border:1px solid var(--line);background:var(--bg2);color:#fff;text-decoration:none}'
                 '.ls img{width:100%;height:100%;object-fit:cover}.ls span{position:absolute;inset:auto 0 0;padding:24px 10px 10px;font-size:.85rem;font-weight:700;line-height:1.5;background:linear-gradient(transparent,rgba(0,0,0,.85))}'
                 '@media (max-width:640px){.sgr{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>')
        home = re.sub(r"<!--LATEST-->.*?<!--/LATEST-->", lambda m: "<!--LATEST-->" + strip + "<!--/LATEST-->", home, flags=re.S)
        open("index.html", "w").write(home)
    # search index + page
    idx = []
    for x in eps:
        sm, ch, _, _ = parse(x["description"])
        tr = transcript(x["id"], ch)
        idx.append({"u": f"episode-{x['id']}.html", "k": "حلقة", "t": x["title"], "s": sm,
                    "c": " · ".join(c["title"] for c in ch), "x": " ".join(y["text"] for y in tr)})
    for k, (slug, name, intro) in TOPIC_PAGES.items():
        if any(topic(x["title"]) == k for x in eps + shorts):
            idx.append({"u": f"topic-{slug}.html", "k": "موضوع", "t": name, "s": intro, "c": "", "x": ""})
    for x in shorts:
        idx.append({"u": f"short-{x['id']}.html", "k": "شورت", "t": x["title"], "s": "", "c": "", "x": ""})
    json.dump(idx, open("data/search.json", "w"), ensure_ascii=False)
    sbody = CSS + open("search.src.html").read()
    page("search.html", "بحث · شنو السالفة؟", "ابحث في حلقات «شنو السالفة؟»: العناوين والفصول والنص الكامل.", sbody, nav="search.html")
    # RSS feed
    from email.utils import format_datetime
    import datetime as dt
    items = "".join(
        f"<item><title>{e_(x['title'])}</title><link>{BASE}episode-{x['id']}.html</link><guid isPermaLink=\"true\">{BASE}episode-{x['id']}.html</guid>"
        f"<pubDate>{format_datetime(dt.datetime.fromisoformat(x['published'].replace('Z', '+00:00')))}</pubDate>"
        f"<description>{e_(parse(x['description'])[0])}</description></item>" for x in eps)
    open("feed.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f'<title>حلقات شنو السالفة؟</title><link>{BASE}episodes.html</link><description>حلقات «شنو السالفة؟» الطويلة باللهجة البحرينية</description><language>ar</language>'
        f'<atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/>{items}</channel></rss>\n')
    sitems = "".join(
        f"<item><title>{e_(x['title'])}</title><link>{BASE}short-{x['id']}.html</link><guid isPermaLink=\"true\">{BASE}short-{x['id']}.html</guid>"
        f"<pubDate>{format_datetime(dt.datetime.fromisoformat(x['published'].replace('Z', '+00:00')))}</pubDate></item>" for x in shorts)
    open("feed-shorts.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f'<title>شورتس شنو السالفة؟</title><link>{BASE}episodes.html</link><description>شورتس «شنو السالفة؟» باللهجة البحرينية</description><language>ar</language>'
        f'<atom:link href="{BASE}feed-shorts.xml" rel="self" type="application/rss+xml"/>{sitems}</channel></rss>\n')
    # llms.txt: plain-text map of the site for AI search tools
    L = ["# شنو السالفة؟ · Salfa Studio", "",
         "> قناة بحرينية تشرح القصص الكبيرة باللهجة البحرينية، بمصدرين لكل رقم. هذا الموقع فيه ملخص كل حلقة وفصولها ومصادرها.",
         "> A Bahraini Arabic explainer channel (YouTube/TikTok @shnoalsalfa_bh). Each episode page has a summary, chapters, sources and, where available, the full transcript.", "",
         "## الحلقات / Episodes"]
    for x in eps:
        L.append(f"- [{x['title']}]({BASE}episode-{x['id']}.html): {parse(x['description'])[0][:200]}")
    L += ["", "## المواضيع / Topics"]
    for k, (slug, name, intro) in TOPIC_PAGES.items():
        if any(topic(x["title"]) == k for x in eps + shorts):
            L.append(f"- [{name}]({BASE}topic-{slug}.html): {intro}")
    L += ["", "## عن الموقع / About", f"- [من نحن]({BASE}about.html): شلون نشتغل وقواعدنا وتصحيح الأخطاء",
          f"- [English]({BASE}en.html): what Salfa Studio is, permissions and data handling", f"- [بحث]({BASE}search.html)", f"- [أفكار الحلقات]({BASE}ideas.html): اقتراح مواضيع والتصويت عليها", f"- [تواصل]({BASE}contact.html): تصحيح معلومة أو سؤال", f"- [أعلن معنا]({BASE}advertise.html): الإعلان والرعاية",
          f"- [RSS]({BASE}feed.xml)", ""]
    open("llms.txt", "w").write("\n".join(L))
    # sitemap
    sm = open("sitemap.xml").read()
    sm = re.sub(r"<url><loc>[^<]*(?:episodes|episode-|topic-|short-|en\\.html)[^<]*</loc>.*?</url>", "", sm)
    add = "".join(f"<url><loc>{BASE}{p}</loc><lastmod>{d}</lastmod></url>" for p, d in
                  [("episodes.html", eps[0]["published"][:10]), ("en.html", "2026-11-23")] + [(f"episode-{e['id']}.html", e["published"][:10]) for e in eps]
                  + [(f"short-{x['id']}.html", x["published"][:10]) for x in shorts]
                  + [(f"topic-{v[0]}.html", eps[0]["published"][:10]) for k, v in TOPIC_PAGES.items() if any(topic(x["title"]) == k for x in eps + shorts)])
    open("sitemap.xml", "w").write(sm.replace("</urlset>", add + "</urlset>"))
    print("built", len(eps), "episode pages")


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    build()
