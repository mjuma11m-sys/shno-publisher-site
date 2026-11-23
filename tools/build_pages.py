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
stamp_index()
print("pages built")
