"""Parse eventpages/*.html -> events_detail.json keyed by event id."""
import glob
import json
import re

from bs4 import BeautifulSoup

def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()

out = {}
for path in sorted(glob.glob('eventpages/*.html')):
    m = re.match(r'.*/([a-z-]+)_(\d+)\.html$', path)
    if not m:
        print('skip', path)
        continue
    etype, eid = m.group(1), m.group(2)
    soup = BeautifulSoup(open(path).read(), 'lxml')
    d = {'type': etype}

    t = soup.select_one('.event-title')
    d['title'] = clean(t.get_text()) if t else None

    pills = [clean(p.get_text()) for p in soup.select('.meta-pill')]
    d['meta_pills'] = pills
    for p in pills:
        if re.search(r'\d{4}', p) and ('AM' in p or 'PM' in p):
            d['datetime_pdt'] = p
        elif not re.search(r'\d{1,2}:\d{2}', p):
            d['room'] = p

    ab = soup.select_one('.abstract-text-inner')
    if ab:
        d['abstract_html'] = str(ab.decode_contents()).strip()

    org = soup.select_one('[class*=organizer]')
    if org:
        d['organizers'] = clean(org.get_text())

    speakers = []
    for row in soup.select('.speaker-bio-row'):
        name = row.select_one('.speaker-bio-name')
        bio = row.select_one('.speaker-bio-text')
        speakers.append({
            'name': clean(name.get_text()) if name else None,
            'bio': clean(bio.get_text()) if bio else None,
        })
    if speakers:
        d['speakers'] = speakers

    links = []
    for a in soup.select('.hero-header-row a[href], .eventmedia a[href], a.btn[href]'):
        href = a.get('href', '')
        txt = clean(a.get_text())
        if href.startswith('http') and txt and txt.lower() not in ('email',):
            links.append({'label': txt, 'url': href})
    # also openreview links anywhere in header area
    for a in soup.select('a[href*="openreview"]'):
        href = a['href']
        if not any(l['url'] == href for l in links):
            links.append({'label': 'OpenReview', 'url': href})
    if links:
        seen = set()
        uniq = []
        for l in links:
            if l['url'] in seen:
                continue
            seen.add(l['url'])
            uniq.append(l)
        d['links'] = uniq[:6]

    out[eid] = d

json.dump(out, open('events_detail.json', 'w'), indent=1, ensure_ascii=False)
print('parsed', len(out), 'event pages')
have_abs = sum(1 for v in out.values() if v.get('abstract_html'))
print('with abstract:', have_abs)
from collections import Counter
print(Counter(v['type'] for v in out.values()))
