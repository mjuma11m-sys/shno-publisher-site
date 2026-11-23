"""Shared page shell: takes index.html's header/footer and sets per-page title, description, canonical, Open Graph, hreflang and nav state."""
import html, json, re

BASE = "https://mjuma11m-sys.github.io/shno-publisher-site/"
_src = open("index.html").read()
HEAD, _rest = _src.split("<main>", 1)
FOOT = "</main>" + _rest.split("</main>", 1)[1]


def page(path, title, desc, body, nav=None, image=None, og_type="website", ld=None):
    e = lambda s: html.escape(s, quote=True)
    url = BASE + ("" if path == "index.html" else path)
    h = re.sub(r"<title>.*?</title>", f"<title>{e(title)}</title>", HEAD, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(desc)}">', h, count=1)
    h = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', h, count=1)
    h = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{e(title)}">', h, count=1)
    h = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{e(desc)}">', h, count=1)
    if image:
        h = re.sub(r'<meta property="og:image" content="[^"]*">', f'<meta property="og:image" content="{image}">', h, count=1)
    h = re.sub(r'<meta property="og:type" content="[^"]*">', f'<meta property="og:type" content="{og_type}">', h, count=1)
    h = re.sub(r'\n?<meta (property="og:url"|name="twitter:card")[^>]*>|\n?<link rel="alternate" (hreflang|type="application/rss)[^>]*>', "", h)
    extra = (f'<meta property="og:url" content="{url}">\n<meta name="twitter:card" content="summary_large_image">\n'
             f'<link rel="alternate" hreflang="ar" href="{BASE}">\n<link rel="alternate" hreflang="en" href="{BASE}en.html">\n'
             f'<link rel="alternate" hreflang="x-default" href="{BASE}">\n'
             f'<link rel="alternate" type="application/rss+xml" title="حلقات شنو السالفة؟" href="{BASE}feed.xml">')
    if ld is not None:
        h = re.sub(r'<script type="application/ld\+json">.*?</script>', "", h, flags=re.S)
        extra += f'\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    h = h.replace("</head>", extra + "\n</head>", 1)
    h = h.replace(' aria-current="page"', "")
    if nav:
        h = h.replace(f'<a href="{nav}">', f'<a href="{nav}" aria-current="page">', 1)
    open(path, "w").write(h + "<main>" + body + FOOT)


def stamp_index():
    """Give index.html the same og:url / hreflang / RSS links (idempotent)."""
    global HEAD
    h = re.sub(r'\n?<meta (property="og:url"|name="twitter:card")[^>]*>|\n?<link rel="alternate" (hreflang|type="application/rss)[^>]*>', "", _src)
    extra = (f'<meta property="og:url" content="{BASE}">\n<meta name="twitter:card" content="summary_large_image">\n'
             f'<link rel="alternate" hreflang="ar" href="{BASE}">\n<link rel="alternate" hreflang="en" href="{BASE}en.html">\n'
             f'<link rel="alternate" hreflang="x-default" href="{BASE}">\n'
             f'<link rel="alternate" type="application/rss+xml" title="حلقات شنو السالفة؟" href="{BASE}feed.xml">')
    open("index.html", "w").write(h.replace("</head>", extra + "\n</head>", 1))
