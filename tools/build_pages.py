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
