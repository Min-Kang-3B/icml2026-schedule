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
ko_pabs = load('ko_pabs.json')
ko_wtitles = load('ko_wtitles.json')
ko_wabs = load('ko_wabs.json')
or_venues = load('or_venues.json')
w_matches = load('workshop_matches.json')
ws_extract = load('ws_extract.json')     # wid -> {has_schedule,tz,schedule,speakers}
ws_projpages = load('ws_projpages.json') # wid -> {title, proj}
ws_paper_tags = load('ws_paper_tags.json')  # paper_id -> "Oral" | "Spotlight" (OpenReview designation)
ws_manual_poster = load('ws_manual_poster.json')  # wid -> {posterLoc, note_ko, note_en} from off-site sources (email / on-site slides)

def poster_locations(schedule):
    """Pull concise 'Hall X · <board ranges>' strings from poster-session rows that carry a location."""
    locs = []
    for it in schedule:
        if it.get('kind') != 'poster':
            continue
        en = it.get('en', '') or ''
        m = re.search(r'((?:Row\s*[\d\-–,\s]+in\s*)?(?:Hall|Room)\s*[A-E]\d?\b[^)\n]*)', en, re.I)
        if not m:
            continue
        loc = m.group(1)
        loc = loc.replace('(', ' ').replace(')', ' ')   # avoid dangling parens
        loc = re.sub(r'\s*,?\s*inclusive\s*', ' ', loc, flags=re.I)
        loc = re.sub(r'\s+', ' ', loc).strip(' ,.')
        if loc and loc not in locs:
            locs.append(loc)
    return locs

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
    if ko_pabs.get(pid):
        ent['absKo'] = ko_pabs[pid]
    return ent

import html as _html

def or_abs_html(text):
    """OpenReview abstracts are plain text; escape and wrap paragraphs."""
    if not text:
        return None
    paras = [p.strip() for p in re.split(r'\n\s*\n|\n', text) if p.strip()]
    return ''.join(f'<p>{_html.escape(p)}</p>' for p in paras)

def workshop_paper_entry(p):
    ent = {'id': p['id'], 'en': p.get('title')}
    if ko_wtitles.get(p['id']):
        ent['ko'] = ko_wtitles[p['id']]
    authors = p.get('authors')
    if isinstance(authors, list):
        ent['authors'] = ', '.join(authors)
    elif authors:
        ent['authors'] = str(authors)
    ab = or_abs_html(p.get('abstract'))
    if ab:
        ent['abs'] = ab
    if ko_wabs.get(p['id']):
        ent['absKo'] = ko_wabs[p['id']]
    if p.get('forum'):
        ent['link'] = p['forum']
    tag = ws_paper_tags.get(p['id'])
    if tag:
        ent['tag'] = tag
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
            # keep session identifiers (e.g. "Oral 1A") visible in Korean titles,
            # stripping any translated duplicate ("구두 발표 1A", "오럴 1A", ...)
            m = re.match(r'^(Oral \d[A-Z]?)\s', e['title'])
            if m and m.group(1) not in ko_t:
                body = re.sub(r'^(?:Oral|오럴|구두\s*발표|구두)\s*\d[A-Z]?\s*[:·\-]?\s*', '', ko_t)
                ko_t = f"{m.group(1)} · {body or ko_t}"
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
            drec['links'] = list(det['links'])

        # workshop program (schedule + invited speakers) scraped from the workshop's own site
        if e['type'] == 'workshop':
            proj = (ws_projpages.get(eid) or {}).get('proj')
            if proj:
                drec.setdefault('links', [])
                if not any(l.get('url') == proj for l in drec['links']):
                    drec['links'].insert(0, {'label': 'Workshop site', 'url': proj})
            prog = ws_extract.get(eid)
            if prog and (prog.get('schedule') or prog.get('speakers')):
                p = {}
                if prog.get('has_schedule') and prog.get('schedule'):
                    p['tz'] = prog.get('tz') or ''
                    sched_out = []
                    for it in prog['schedule']:
                        if not (it.get('en') or it.get('speaker')):
                            continue
                        row = {k: it.get(k, '') for k in ('time', 'en', 'ko', 'speaker', 'kind')}
                        subs = it.get('items')
                        if isinstance(subs, list) and subs:
                            row['items'] = [
                                {k: s.get(k, '') for k in ('en', 'ko', 'speaker')}
                                for s in subs if s.get('en')
                            ]
                        sched_out.append(row)
                    p['schedule'] = sched_out
                # dedupe speakers by name, keep those with a real name
                seen = set(); sp2 = []
                for sp in prog.get('speakers', []):
                    nm = (sp.get('name') or '').strip()
                    if nm and nm.lower() not in seen:
                        seen.add(nm.lower())
                        sp2.append({'name': nm, 'affil': sp.get('affil', '') or '', 'role': sp.get('role', '') or ''})
                if sp2:
                    p['speakers'] = sp2
                if p.get('schedule'):
                    plocs = poster_locations(p['schedule'])
                    if plocs:
                        p['posterLoc'] = plocs
                        ev['posterLoc'] = plocs   # surface on the card (schedule.js) too
                # manual poster info from off-site sources (organizer email / on-site slide) overrides
                man = ws_manual_poster.get(eid)
                if man:
                    if man.get('posterLoc'):
                        p['posterLoc'] = man['posterLoc']
                        ev['posterLoc'] = man['posterLoc']
                    note = {}
                    if man.get('note_ko'):
                        note['ko'] = man['note_ko']
                    if man.get('note_en'):
                        note['en'] = man['note_en']
                    if note:
                        p['posterNote'] = note
                if p.get('schedule') or p.get('speakers') or p.get('posterLoc'):
                    drec['program'] = p

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

        # workshop / affinity-event accepted papers from OpenReview
        if eid in w_matches:
            venue = or_venues.get(w_matches[eid], {})
            wp = [workshop_paper_entry(p) for p in venue.get('papers', []) if p.get('title')]
            if wp:
                # surface orally-presented papers first: Oral, then Spotlight, then the rest (stable)
                rank = {'Oral': 0, 'Spotlight': 1}
                wp.sort(key=lambda e: rank.get(e.get('tag'), 2))
                paper_files[eid] = wp
                ev['nPapers'] = len(wp)
                ev['papersSource'] = 'openreview'
                nprom = sum(1 for e in wp if e.get('tag'))
                if nprom:
                    ev['nPromoted'] = nprom

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
