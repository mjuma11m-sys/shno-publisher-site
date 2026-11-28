"""Rebuild the data pages (office, office-2d, dashboard) and the static pages (about, en) from *.src.html + data/*.json.
Usage: python3 tools/build_pages.py"""
import json, os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "tools")
from shell import page, stamp_index

office = "window.OFFICE=" + json.dumps(json.load(open("data/office.json")), ensure_ascii=False) + ";"
dash = "window.DASH=" + json.dumps(json.load(open("data/dashboard.json")), ensure_ascii=False) + ";"
OD = "مكتب افتراضي يعرض فريق وكلاء الذكاء الاصطناعي اللي يشتغل على قناة «شنو السالفة؟»: منو يشتغل، وشنو الجاي."
page("office.html", "مكتب سالفة ستوديو · Salfa Studio", OD, open("office3d.src.html").read().replace("/*DATA*/", office), nav="office.html")
page("office-2d.html", "مكتب سالفة ستوديو (مسطّح) · Salfa Studio", OD, open("office.src.html").read().replace("/*DATA*/", office), nav="office.html")
page("dashboard.html", "لوحة التحكم · Salfa Studio", "أرقام قناة «شنو السالفة؟» الحقيقية من YouTube Data API: المشاهدات لكل فيديو، المواضيع، طابور النشر والموافقات.",
     open("dashboard.src.html").read().replace("/*DATA*/", dash), nav="dashboard.html")
page("about.html", "من نحن · شنو السالفة؟", "«شنو السالفة؟» قناة بحرينية تشرح القصص الكبيرة باللهجة البحرينية بمصدرين لكل رقم. شلون نشتغل، قواعدنا، وشلون نصحّح الغلط.",
     open("about.src.html").read(), nav="about.html")
page("en.html", "Salfa Studio · About in English", "Salfa Studio is the in-house tool that publishes the Bahraini channel «شنو السالفة؟» videos to its own YouTube and TikTok accounts. Scopes, data handling and policies.",
     open("en.src.html").read(), nav="en.html")
page("advertise.html", "أعلن معنا · شنو السالفة؟", "الإعلان والرعاية في قناة «شنو السالفة؟» على يوتيوب وتيك توك: الأرقام المباشرة، طرق التعاون، وشروطنا.", open("advertise.src.html").read())
page("contact.html", "تواصل معنا · شنو السالفة؟", "تواصل مع قناة «شنو السالفة؟»: تصحيح معلومة، سؤال، أو فكرة حلقة.", open("contact.src.html").read())
page("ideas.html", "أفكار الحلقات · شنو السالفة؟", "اقترح موضوع حلقة لقناة «شنو السالفة؟» وصوّت للأفكار اللي تعجبك.", open("ideas.src.html").read(), nav="ideas.html")
page("support.html", "ادعمنا · شنو السالفة؟", "شلون تدعم قناة «شنو السالفة؟» البحرينية: اشترك، شارك، علّق، واقترح مواضيع.", open("support.src.html").read(), nav="about.html")
stamp_index()
print("pages built")
page("studio.html", "النشر · Salfa Studio", "صفحة صاحب قناة «شنو السالفة؟» لنشر فيديوهات القناة على يوتيوب وتيك توك بعد مراجعتها.",
     open("studio.src.html").read())
s = open("studio.html").read()
if 'name="robots"' not in s:
    open("studio.html", "w").write(s.replace("</head>", '<meta name="robots" content="noindex">\n</head>', 1))
print("studio built")

# Offline fallback for the installed app (served by sw.js when there is no connection and the page is not cached)
page("offline.html", "ما فيه إنترنت · Salfa Studio", "الصفحة هذي تطلع لما ينقطع الإنترنت وأنت فاتح تطبيق سالفة ستوديو.",
     '<div class="wrap" style="padding-block:48px;text-align:center"><h1>ما فيه إنترنت 📡</h1>'
     '<p class="muted">الصفحات اللي فتحتها قبل تشتغل بدون إنترنت. هالصفحة للحين ما انحفظت.</p>'
     '<p style="margin-top:18px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap">'
     '<a class="btn pri" href="/">الرئيسية</a><a class="btn sec" href="/episodes.html">الحلقات</a>'
     '<button class="btn sec" type="button" onclick="location.reload()">جرّب مرة ثانية</button></p></div>')
s = open("offline.html").read()
if 'name="robots"' not in s:
    open("offline.html", "w").write(s.replace("</head>", '<meta name="robots" content="noindex">\n</head>', 1))
print("offline built")

# «أفضل ما عندنا»: top 10 videos by real YouTube views (from data/dashboard.json) — the bio link page
import html as _h
_D = json.load(open("data/dashboard.json"))
_top = sorted(_D["videos"], key=lambda v: -v.get("views", 0))[:10]
def _href(v):
    for p in (f"short-{v['id']}.html", f"episode-{v['id']}.html"):
        if os.path.exists(p):
            return p
    return f"https://www.youtube.com/watch?v={v['id']}"
_cards = "".join(
    f'<a class="lc" href="{_href(v)}"><img src="https://i.ytimg.com/vi/{v["id"]}/{"hqdefault" if v["type"]=="short" else "mqdefault"}.jpg" alt="" loading="lazy" width="320" height="180">'
    f'<b>{_h.escape(v["title"].split("#")[0].strip())}</b><small>{v["views"]:,} مشاهدة · {"شورت" if v["type"]=="short" else "حلقة"} · {v["topic"]}</small></a>'
    for v in _top)
_best = f'''<style>.best{{padding-block:28px 8px;display:grid;gap:18px}}.best h1{{margin:0;font:900 clamp(1.6rem,3.6vw,2.4rem)/1.3 "Tajawal",sans-serif;text-wrap:balance}}
.best .lead{{color:var(--mut);margin:0;max-width:65ch}}.bgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}}
.bgrid .lc{{display:grid;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:10px;color:var(--fg);text-decoration:none;min-width:0}}
.bgrid .lc img{{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;border-radius:10px;background:var(--bg2)}}.bgrid .lc small{{color:var(--mut)}}
.subbar{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:16px 18px}}</style>
<div class="wrap"><article class="best"><div><h1>أفضل ما عندنا 🔥</h1><p class="lead">أكثر 10 فيديوهات انشافت بقناة «شنو السالفة؟» على يوتيوب (أرقام حقيقية، تحديث {_D["updated"][:10]}). كل رقم بمصدرين، والصوت بالذكاء الاصطناعي.</p></div>
<div class="subbar"><b style="flex:1 1 200px">عجبك؟ القصة الجاية تنزل الأربعاء والأحد 8 بالليل.</b><a class="btn pri" href="https://www.youtube.com/@shnoalsalfa_bh?sub_confirmation=1" rel="noopener">🔔 اشترك بيوتيوب</a><a class="btn sec" href="https://www.tiktok.com/@shnoalsalfa_bh" rel="noopener">تيك توك</a></div>
<div class="bgrid">{_cards}</div></article></div>'''
page("best.html", "أفضل ما عندنا · شنو السالفة؟", "أكثر 10 فيديوهات انشافت بقناة «شنو السالفة؟» البحرينية: تاريخ البحرين، GTA بالأرقام، والخليج — بأرقام حقيقية من يوتيوب.", _best, nav="episodes.html")
print("best built")
