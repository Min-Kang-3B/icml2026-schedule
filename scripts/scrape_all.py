"""Bulk-fetch ICML 2026 detail pages.
- Papers (posters + orals): extract abstract inline -> abstracts.jsonl
- Simple events (workshops, invited talks, socials, ...): save raw HTML -> eventpages/
"""
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

BASE = 'https://icml.cc'
HDRS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'}

sched = json.load(open('schedule_raw.json'))
papers = json.load(open('papers.json'))['results']
by_title = {}
for r in papers:
    by_title.setdefault(r['name'].strip().lower(), r)

# ---- build work lists ----
paper_urls = {}   # id -> url
event_urls = {}   # id -> url  (simple events; session pages need login -> skip)
for day in sched['days']:
    for e in day['events']:
        if e['kind'] == 'simple':
            event_urls[e['id']] = e['url']
        for c in e.get('children', []):
            if c.get('url'):
                paper_urls[c['id']] = c['url']
            else:
                rec = by_title.get(c['title'].strip().lower())
                if rec and rec.get('virtualsite_url'):
                    paper_urls[str(rec['id'])] = rec['virtualsite_url']

os.makedirs('eventpages', exist_ok=True)

# resume support
done_papers = set()
if os.path.exists('abstracts.jsonl'):
    for line in open('abstracts.jsonl'):
        try:
            done_papers.add(json.loads(line)['id'])
        except Exception:
            pass
paper_todo = {k: v for k, v in paper_urls.items() if k not in done_papers}
event_todo = {k: v for k, v in event_urls.items()
              if not os.path.exists(f'eventpages/{v.strip("/").replace("/", "_").replace("virtual_2026_", "")}.html')}

print(f'papers: {len(paper_urls)} total, {len(paper_todo)} to fetch')
print(f'events: {len(event_urls)} total, {len(event_todo)} to fetch', flush=True)

lock = threading.Lock()
out = open('abstracts.jsonl', 'a')
counter = {'n': 0, 'err': 0}

session_local = threading.local()
def get_session():
    if not hasattr(session_local, 's'):
        s = requests.Session()
        s.headers.update(HDRS)
        session_local.s = s
    return session_local.s

def fetch(url, tries=3):
    for i in range(tries):
        try:
            r = get_session().get(BASE + url, timeout=25)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        time.sleep(1 + 2 * i)
    return None

def extract_abstract(html):
    soup = BeautifulSoup(html, 'lxml')
    inner = soup.select_one('.abstract-text-inner')
    if inner:
        return str(inner.decode_contents()).strip()
    return None

def do_paper(pid, url):
    html = fetch(url)
    rec = {'id': pid, 'url': url}
    if html is None:
        rec['error'] = True
    else:
        rec['abstract'] = extract_abstract(html)
    with lock:
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        counter['n'] += 1
        if html is None:
            counter['err'] += 1
        if counter['n'] % 200 == 0:
            out.flush()
            print(f"{counter['n']}/{len(paper_todo)} papers ({counter['err']} errors)", flush=True)

def do_event(eid, url):
    html = fetch(url)
    if html:
        name = url.strip('/').replace('/', '_').replace('virtual_2026_', '')
        with open(f'eventpages/{name}.html', 'w') as f:
            f.write(html)
    else:
        with lock:
            print('EVENT FAIL', url, flush=True)

t0 = time.time()
with ThreadPoolExecutor(max_workers=12) as ex:
    futs = [ex.submit(do_event, k, v) for k, v in event_todo.items()]
    futs += [ex.submit(do_paper, k, v) for k, v in paper_todo.items()]
    for f in as_completed(futs):
        f.result()
out.close()
print(f'DONE in {time.time()-t0:.0f}s: {counter["n"]} papers, {counter["err"]} errors', flush=True)
