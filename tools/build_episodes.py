"""Episode pages for the long «شنو السالفة؟» videos.

  python3 tools/build_episodes.py --fetch   # pull long videos from YouTube Data API into data/episodes.json, then build
  python3 tools/build_episodes.py           # build episodes.html + episode-<id>.html from data/episodes.json

The API key is injected by the network proxy (header x-goog-api-key); nothing secret lives here.
"""
import html, json, os, re, sys, urllib.request
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = "https://mjuma11m-sys.github.io/shno-publisher-site/"
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


def mmss(s):
    return f"{s // 60}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


sys.path.insert(0, "tools")
from shell import page


CSS = """<style>
.ep{padding-block:28px 8px;display:grid;gap:20px}
.crumb{color:var(--mut);font-size:.88rem}.crumb a{color:var(--mut)}
.ep h1{margin:0;font:900 clamp(1.5rem,3.2vw,2.3rem)/1.3 "Tajawal",sans-serif;text-wrap:balance}
.meta{display:flex;gap:8px;flex-wrap:wrap;color:var(--mut);font-size:.88rem}.meta span{border:1px solid var(--line);border-radius:999px;padding:4px 12px;background:var(--bg2)}
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
    e_ = html.escape
    for e in eps:
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
        tr = transcript(e["id"], chapters)
        if tr:
            ld["transcript"] = " ".join(x["text"] for x in tr)
        tr_html = ("" if not tr else '<details class="box tr"><summary><h2>النص الكامل للحلقة</h2><span>من ترجمة الحلقة · ' + str(len(tr)) + ' فصل</span></summary>'
                   + "".join(f'<section><h3><a href="{watch}&amp;t={x["t"]}s" target="_blank" rel="noopener">{mmss(x["t"])}</a> {e_(x["title"])}</h3><p>{e_(x["text"])}</p></section>' for x in tr) + "</details>")
        body = f"""{CSS}<div class="wrap"><article class="ep">
<nav class="crumb" aria-label="مسار الصفحة"><a href="episodes.html">الحلقات</a> ‹ {e_(e['title'][:40])}</nav>
<h1>{e_(e['title'])}</h1>
<div class="meta"><span class="pill">{ardate(e['published'])}</span><span class="pill">{mmss(e['secs'])} دقيقة</span><span class="pill">باللهجة البحرينية</span></div>
<a class="poster" href="{watch}" target="_blank" rel="noopener"><img src="{thumb}" alt="غلاف حلقة {e_(e['title'])}" loading="eager" width="1280" height="720"><span>▶ شوف الحلقة على يوتيوب</span></a>
<div class="ecols">
 <div style="display:grid;gap:20px;align-content:start">
  <section class="box"><h2>شنو السالفة؟</h2><p class="lead">{e_(summary)}</p></section>
  <section class="box"><h2>المصادر والحقوق</h2><ul class="cred">{''.join(f'<li>{e_(c)}</li>' for c in credits) or '<li>المصادر بوصف الفيديو على يوتيوب.</li>'}</ul></section>
  <div class="tags">{''.join(f'<span>#{e_(t)}</span>' for t in tags)}</div>
 </div>
 <section class="box"><h2>الفصول</h2><ol class="chap">{''.join(f'<li><a href="{watch}&amp;t={c["t"]}s" target="_blank" rel="noopener"><b>{c["label"]}</b><span>{e_(c["title"])}</span></a></li>' for c in chapters)}</ol></section>
</div>
{tr_html}
</article></div>"""
        title = f"{e['title']} · شنو السالفة؟"
        page(f"episode-{e['id']}.html", title, summary[:155], body, nav="episodes.html", image=thumb, og_type="video.other", ld=ld)
    shorts = json.load(open("data/shorts.json")) if os.path.exists("data/shorts.json") else []
    shorts_html = ""
    if shorts:
        used = [k for k in list(TOPICS) + ["أخرى"] if any(topic(x["title"]) == k for x in shorts)]
        chips = '<button type="button" data-t="" aria-pressed="true">الكل</button>' + "".join(f'<button type="button" data-t="{k}" aria-pressed="false">{k}</button>' for k in used)
        tiles = "".join(f'<a class="sh" data-t="{topic(x["title"])}" href="https://www.youtube.com/shorts/{x["id"]}" target="_blank" rel="noopener"><img src="{x["thumb"]}" alt="" loading="lazy" width="480" height="360"><span>{e_(x["title"])}</span></a>' for x in shorts)
        shorts_html = (f'<div style="display:grid;gap:12px;margin-top:12px"><h2 style="margin:0;font:900 1.5rem Tajawal,sans-serif">الشورتس <small style="color:var(--mut);font-size:.9rem;font-weight:400">{len(shorts)}</small></h2>'
                       f'<div class="chips" role="group" aria-label="الموضوع">{chips}</div><div class="sgrid">{tiles}</div></div>'
                       '<script>document.querySelectorAll(".chips button").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".chips button").forEach(x=>x.setAttribute("aria-pressed",x===b));document.querySelectorAll(".sh").forEach(a=>a.hidden=!!b.dataset.t&&a.dataset.t!==b.dataset.t)}))</script>')
    cards = "".join(f'<a class="card3" href="episode-{e["id"]}.html"><img src="https://i.ytimg.com/vi/{e["id"]}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180"><div><b>{e_(e["title"])}</b><small>{ardate(e["published"])} · {mmss(e["secs"])} دقيقة</small></div></a>' for e in eps)
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "حلقات شنو السالفة؟",
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{BASE}episode-{e['id']}.html"} for i, e in enumerate(eps)]}
    body = f"""{CSS}<div class="wrap"><section class="ep"><div><h1>الحلقات</h1><p style="color:var(--mut);margin:6px 0 0">كل حلقات «شنو السالفة؟» الطويلة: الملخص والفصول ومصادر كل حلقة.</p></div><div class="grid">{cards}</div>{shorts_html}</section></div>"""
    page("episodes.html", "الحلقات · شنو السالفة؟", "كل حلقات «شنو السالفة؟» باللهجة البحرينية: الحلقات الطويلة بملخصها وفصولها ومصادرها، والشورتس حسب الموضوع.", body, nav="episodes.html", ld=ld)
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
    # sitemap
    sm = open("sitemap.xml").read()
    sm = re.sub(r"<url><loc>[^<]*(?:episodes|episode-|en\\.html)[^<]*</loc>.*?</url>", "", sm)
    add = "".join(f"<url><loc>{BASE}{p}</loc><lastmod>{d}</lastmod></url>" for p, d in
                  [("episodes.html", eps[0]["published"][:10]), ("en.html", "2026-11-23")] + [(f"episode-{e['id']}.html", e["published"][:10]) for e in eps])
    open("sitemap.xml", "w").write(sm.replace("</urlset>", add + "</urlset>"))
    print("built", len(eps), "episode pages")


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    build()
