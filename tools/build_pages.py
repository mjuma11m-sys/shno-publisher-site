"""Rebuild office.html, office-2d.html and dashboard.html from their *.src.html + data/*.json. Usage: python3 tools/build_pages.py"""
import json,re,os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src=open('index.html').read()
head,rest=src.split('<main>',1); foot='</main>'+rest.split('</main>',1)[1]
data='window.OFFICE='+json.dumps(json.load(open('data/office.json')),ensure_ascii=False)+';'
def H(title):
    h=re.sub(r'<title>.*?</title>',f'<title>{title}</title>',head,count=1)
    h=re.sub(r'<meta name="description" content="[^"]*">','<meta name="description" content="مكتب افتراضي يعرض فريق وكلاء الذكاء الاصطناعي اللي يشتغل على قناة «شنو السالفة؟»: منو يشتغل، وشنو الجاي.">',h,count=1)
    return h.replace(' aria-current="page"','').replace('<a href="office.html">','<a href="office.html" aria-current="page">',1)
open('office.html','w').write(H('مكتب سالفة ستوديو · Salfa Studio')+'<main>'+open('office3d.src.html').read().replace('/*DATA*/',data)+foot)
open('office-2d.html','w').write(H('مكتب سالفة ستوديو (مسطّح) · Salfa Studio')+'<main>'+open('office.src.html').read().replace('/*DATA*/',data)+foot)

dd='window.DASH='+json.dumps(json.load(open('data/dashboard.json')),ensure_ascii=False)+';'
hd=H('لوحة التحكم · Salfa Studio').replace(' aria-current="page"','').replace('<a href="dashboard.html">','<a href="dashboard.html" aria-current="page">',1)
open('dashboard.html','w').write(hd+'<main>'+open('dashboard.src.html').read().replace('/*DATA*/',dd)+foot)
