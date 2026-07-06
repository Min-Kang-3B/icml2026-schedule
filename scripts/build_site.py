"""Merge schedule + event details + papers + translations into site data JS files.

Output (to SITE dir):
  data/schedule.js          window.ICML_SCHEDULE
  data/details.js           window.ICML_DETAILS
  data/papers/s<id>.js      window.ICML_PAPERS['<sid>'] = [...]
"""
import json
import os
import re
import sys

SITE = sys.argv[1] if len(sys.argv) > 1 else '.'

def load(path, default=None):
    if os.path.exists(path):
        return json.load(open(path))
    return default if default is not None else {}

sched = load('schedule_raw.json')
events = load('events_detail.json')
papers_raw = load('papers.json')['results']
ko_titles = load('ko_titles.json')
ko_abstracts = load('ko_abstracts.json')
ko_bios = load('ko_bios.json')
ko_misc = load('ko_misc.json')

abstracts = {}
if os.path.exists('abstracts.jsonl'):
    for line in open('abstracts.jsonl'):
        try:
            r = json.loads(line)
            if r.get('abstract'):
                abstracts[r['id']] = r['abstract']
        except Exception:
            pass

by_title = {}
by_id = {}
for r in papers_raw:
    by_title.setdefault(r['name'].strip().lower(), r)
    by_id[str(r['id'])] = r

# ---------- time normalization (calendar labels are KST) ----------
def norm_time(label):
    """'7:30 a.m.' / '10 a.m.' / 'noon' / '12:30 p.m.' / '6:00 PM' / '10:00' -> 'HH:MM'"""
    if not label:
        return None
    s = label.strip().lower().replace('.', '')
    if s == 'noon':
        return '12:00'
    if s == 'midnight':
        return '00:00'
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$', s)
    if not m:
        return None
    h = int(m.group(1))
    mi = int(m.group(2) or 0)
    ap = m.group(3)
    if ap == 'pm' and h != 12:
        h += 12
    if ap == 'am' and h == 12:
        h = 0
    return f'{h:02d}:{mi:02d}'

TYPE_INFO = {
    'invited-talk':          {'en': 'Invited Talk',        'ko': '초청 강연'},
    'oral-session':          {'en': 'Oral Session',        'ko': '오럴 세션'},
    'poster-session':        {'en': 'Poster Session',      'ko': '포스터 세션'},
    'workshop':              {'en': 'Workshop',            'ko': '워크숍'},
    'social':                {'en': 'Social',              'ko': '소셜'},
    'affinity-event':        {'en': 'Affinity Event',      'ko': '어피니티 이벤트'},
    'affinity-poster-session': {'en': 'Affinity Posters',  'ko': '어피니티 포스터'},
    'break':                 {'en': 'Break',               'ko': '휴식'},
    'registration-desk':     {'en': 'Registration',        'ko': '등록 데스크'},
    'town-hall':             {'en': 'Town Hall',           'ko': '타운홀'},
    'test-of-time':          {'en': 'Test of Time Award',  'ko': 'Test of Time 어워드'},
    'remarks':               {'en': 'Remarks',             'ko': '개회사'},
    'reception':             {'en': 'Reception',           'ko': '리셉션'},
}

DAY_LABELS = {
    3: {'en': 'Tue · Jul 7',  'ko': '화 · 7/7'},
    4: {'en': 'Wed · Jul 8',  'ko': '수 · 7/8'},
    5: {'en': 'Thu · Jul 9',  'ko': '목 · 7/9'},
    6: {'en': 'Fri · Jul 10', 'ko': '금 · 7/10'},
    7: {'en': 'Sat · Jul 11', 'ko': '토 · 7/11'},
}
DATE_FULL = {
    3: {'en': 'Tuesday, July 7, 2026',   'ko': '2026년 7월 7일 화요일'},
    4: {'en': 'Wednesday, July 8, 2026', 'ko': '2026년 7월 8일 수요일'},
    5: {'en': 'Thursday, July 9, 2026',  'ko': '2026년 7월 9일 목요일'},
    6: {'en': 'Friday, July 10, 2026',   'ko': '2026년 7월 10일 금요일'},
    7: {'en': 'Saturday, July 11, 2026', 'ko': '2026년 7월 11일 토요일'},
}

def paper_entry(pid, fallback_title=None, time=None):
    rec = by_id.get(pid)
    ent = {'id': pid}
    ent['en'] = rec['name'] if rec else fallback_title
    ko = ko_titles.get(pid)
    if ko:
        ent['ko'] = ko
    if rec:
        ent['authors'] = ', '.join(a['fullname'] for a in rec.get('authors', []))
        if rec.get('poster_position'):
            ent['pos'] = rec['poster_position']
        if rec.get('paper_url'):
            ent['link'] = rec['paper_url']
    if time:
        ent['time'] = time
    ab = abstracts.get(pid)
    if ab:
        ent['abs'] = ab
    return ent

# ---------- build ----------
os.makedirs(os.path.join(SITE, 'data', 'papers'), exist_ok=True)

out_days = []
details = {}
paper_files = {}   # sid -> list

for day in sched['days']:
    d = {
        'day': day['day'],
        'date': day['date'],
        'label': DAY_LABELS[day['day']],
        'dateFull': DATE_FULL[day['day']],
        'events': [],
    }
    for e in day['events']:
        eid = e['id']
        det = events.get(eid, {})
        ev = {
            'id': eid,
            'type': e['type'],
            'kind': e['kind'],
            'typeName': TYPE_INFO.get(e['type'], {'en': e['type'], 'ko': e['type']}),
            'title': {'en': e['title']},
            'start': norm_time(e.get('start')) or norm_time(e.get('time_label')),
            'end': norm_time(e.get('end')),
            'room': det.get('room') or e.get('room'),
        }
        ko_t = ko_misc.get(f't:{eid}')
        if ko_t:
            # keep session identifiers (e.g. "Oral 1A") visible in Korean titles
            m = re.match(r'^(Oral \d[A-Z]?)\s', e['title'])
            if m and m.group(1) not in ko_t:
                ko_t = f"{m.group(1)} · {ko_t}"
            ev['title']['ko'] = ko_t
        if e.get('speaker'):
            ev['speaker'] = e['speaker']
        if det.get('organizers') and det['organizers'] != e.get('speaker'):
            ev['organizers'] = det['organizers']

        # detail record
        drec = {}
        if det.get('abstract_html'):
            drec['abs'] = {'en': det['abstract_html']}
            if ko_abstracts.get(eid):
                drec['abs']['ko'] = ko_abstracts[eid]
        sps = []
        for i, sp in enumerate(det.get('speakers', [])):
            s = {'name': sp.get('name')}
            if sp.get('bio'):
                s['bio'] = {'en': sp['bio']}
                if ko_bios.get(f'{eid}:{i}'):
                    s['bio']['ko'] = ko_bios[f'{eid}:{i}']
            sps.append(s)
        if sps:
            drec['speakers'] = sps
        if det.get('links'):
            drec['links'] = det['links']

        # children -> paper file
        if e.get('children'):
            plist = []
            for c in e['children']:
                if c.get('id'):
                    plist.append(paper_entry(c['id'], c.get('title'), c.get('time')))
                else:
                    rec = by_title.get(c['title'].strip().lower())
                    pid = str(rec['id']) if rec else None
                    if pid:
                        plist.append(paper_entry(pid, c['title'], c.get('time')))
                    else:
                        plist.append({'en': c['title'], 'time': c.get('time')})
            paper_files[eid] = plist
            ev['nPapers'] = len(plist)

        if drec:
            details[eid] = drec
            ev['hasDetail'] = True
        d['events'].append(ev)
    out_days.append(d)

# room list for filters not needed; write files
def write_js(path, varname, obj, assign=False):
    with open(path, 'w') as f:
        if assign:
            f.write(f'{varname} = ')
        else:
            f.write(f'window.{varname} = ')
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';')

write_js(os.path.join(SITE, 'data', 'schedule.js'), 'ICML_SCHEDULE', {'days': out_days})
write_js(os.path.join(SITE, 'data', 'details.js'), 'ICML_DETAILS', details)
for sid, plist in paper_files.items():
    with open(os.path.join(SITE, 'data', 'papers', f's{sid}.js'), 'w') as f:
        f.write(f'window.ICML_PAPERS["{sid}"] = ')
        json.dump(plist, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';')
        f.write(f'window.dispatchEvent(new CustomEvent("papers-loaded",{{detail:"{sid}"}}));')

# stats
n_ev = sum(len(d['events']) for d in out_days)
n_pap = sum(len(v) for v in paper_files.values())
n_ko_t = sum(1 for v in paper_files.values() for p in v if p.get('ko'))
n_abs = sum(1 for v in paper_files.values() for p in v if p.get('abs'))
print(f'days: {len(out_days)}, events: {n_ev}, details: {len(details)}, paper files: {len(paper_files)}, papers: {n_pap}')
print(f'papers with ko title: {n_ko_t}, with abstract: {n_abs}')
print(f'event ko titles: {sum(1 for d in out_days for e in d["events"] if e["title"].get("ko"))}/{n_ev}')
