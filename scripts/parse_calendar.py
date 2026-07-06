"""Parse ICML 2026 calendar HTML -> structured schedule JSON for days 3-7 (Tue Jul 7 - Sat Jul 11)."""
import json
import re
from bs4 import BeautifulSoup

DAYS = {
    3: {"date": "2026-07-07", "label_en": "Tue, Jul 7", "dow": "TUE"},
    4: {"date": "2026-07-08", "label_en": "Wed, Jul 8", "dow": "WED"},
    5: {"date": "2026-07-09", "label_en": "Thu, Jul 9", "dow": "THU"},
    6: {"date": "2026-07-10", "label_en": "Fri, Jul 10", "dow": "FRI"},
    7: {"date": "2026-07-11", "label_en": "SAT, Jul 11", "dow": "SAT"},
}

html = open('calendar.html').read()
soup = BeautifulSoup(html, 'lxml')

def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def label_to_24h(label):
    """'7:30 a.m.' / '10 a.m.' / 'noon' / '1:30 p.m.' -> minutes since midnight, or None"""
    if not label:
        return None
    s = label.strip().lower().replace('.', '')
    if s == 'noon':
        return 12 * 60
    if s == 'midnight':
        return 0
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$', s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2) or 0)
    ap = m.group(3)
    if ap == 'pm' and hh != 12:
        hh += 12
    if ap == 'am' and hh == 12:
        hh = 0
    return hh * 60 + mm

def fmt24(mins):
    if mins is None:
        return None
    return f'{(mins // 60) % 24:02d}:{mins % 60:02d}'

def align_12h(h, m, anchor_mins, horizon=14 * 60):
    """Interpret ambiguous 12h clock time (h:m, no am/pm) as the first 24h time
    >= anchor_mins (within a horizon). Returns minutes since midnight."""
    base = (h % 12) * 60 + m
    for k in range(4):
        cand = base + k * 12 * 60
        if cand >= anchor_mins and cand - anchor_mins <= horizon:
            return cand
    return base if base >= anchor_mins else base + 12 * 60

def parse_room(classes):
    for c in classes:
        if c.startswith('room-'):
            slug = c[len('room-'):]
            return slug.replace('-', ' ').title() if slug else None
    return None

def parse_simple_event(div, time_label):
    """eventsession pad <type> room-X : simple event with title link"""
    classes = div.get('class', [])
    etype = None
    known = ['registration-desk','affinity-event','invited-talk','break','social','workshop',
             'town-hall','test-of-time','remarks','reception','affinity-poster-session','poster','session']
    for c in classes:
        if c in known:
            etype = c
            break
    a = div.select_one('.title-style a')
    if not a:
        return None
    href = a.get('href')
    hdr = div.select_one('.hdr-style')
    speaker = div.select_one('.speaker-style')
    end = div.select_one('.end-time')
    endtxt = clean(end.get_text()) if end else ''
    m = re.search(r'ends\s+(.+?)\)', endtxt)
    start_mins = label_to_24h(time_label)
    end_mins = label_to_24h(m.group(1).replace(' ', '')) if m else None
    ev = {
        'kind': 'simple',
        'type': etype or (href.split('/')[3] if href and len(href.split('/')) > 3 else 'event'),
        'header': clean(hdr.get_text()).rstrip(':') if hdr else None,
        'title': clean(a.get_text()),
        'url': href,
        'id': href.rstrip('/').split('/')[-1] if href else None,
        'speaker': clean(speaker.get_text()) if speaker else None,
        'start': fmt24(start_mins),
        'end': fmt24(end_mins),
        'room': parse_room(classes),
    }
    return ev

def parse_session_block(div, time_label):
    """oral-session / poster-session block with sessiontitle + eventblock children"""
    classes = div.get('class', [])
    stype = 'oral-session' if 'oral-session' in classes else 'poster-session'
    a = div.select_one('.sessiontitle a')
    if not a:
        return None
    stime = a.select_one('.sessiontime')
    timespan = clean(stime.get_text()) if stime else ''
    title = clean(a.get_text().replace(timespan, ''))
    href = a.get('href')
    # sessiontime like "[01:30-02:30]" is a 12h clock without am/pm.
    # Anchor on the timebox label (which has am/pm) to resolve to 24h.
    start_mins = label_to_24h(time_label)
    end_mins = None
    m = re.match(r'\[(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})\]', timespan)
    if m:
        sh, sm, eh, em = (int(x) for x in m.groups())
        if start_mins is None:
            start_mins = sh * 60 + sm  # last resort
        else:
            start_mins = align_12h(sh, sm, start_mins - 30)
        end_mins = align_12h(eh, em, start_mins)
    children = []
    for content in div.select('.content'):
        link = content.find('a')
        txt = clean(content.get_text())
        tm = re.match(r'^\[(\d{1,2}):(\d{2})\]\s*(.*)', txt)
        child = {}
        if tm:
            ch, cm = int(tm.group(1)), int(tm.group(2))
            child['time'] = fmt24(align_12h(ch, cm, start_mins or 0))
            child['title'] = tm.group(3)
        else:
            child['title'] = txt
        if link and link.get('href'):
            child['url'] = link['href']
            child['id'] = link['href'].rstrip('/').split('/')[-1]
        children.append(child)
    ev = {
        'kind': 'session',
        'type': stype,
        'title': title,
        'url': href,
        'id': href.rstrip('/').split('/')[-1] if href else None,
        'start': fmt24(start_mins),
        'end': fmt24(end_mins),
        'room': parse_room(classes),
        'children': children,
    }
    return ev

out = {'days': []}
for dnum, meta in DAYS.items():
    cont = soup.select_one(f'.container2.day-{dnum}')
    assert cont, f'day-{dnum} not found'
    hdr = clean(cont.select_one('.hdrbox').get_text())
    events = []
    for tb in cont.select('.timebox'):
        time_label = clean(tb.select_one('.time').get_text()) if tb.select_one('.time') else None
        for div in tb.find_all('div', recursive=False):
            cl = div.get('class', [])
            if 'timebox' in cl or 'time' in cl:
                continue
        # events may be nested arbitrarily; find direct event divs
        for div in tb.select('.eventsession.pad, .oral-session.pad, .poster-session.pad'):
            cl = div.get('class', [])
            if 'oral-session' in cl or 'poster-session' in cl:
                ev = parse_session_block(div, time_label)
            elif 'eventsession' in cl and 'hdr' not in cl:
                ev = parse_simple_event(div, time_label)
            else:
                ev = None
            if ev:
                ev['time_label'] = time_label
                events.append(ev)
    out['days'].append({'day': dnum, 'header': hdr, **meta, 'events': events})

json.dump(out, open('schedule_raw.json', 'w'), indent=1, ensure_ascii=False)

# summary
for d in out['days']:
    types = {}
    nchild = 0
    for e in d['events']:
        types[e['type']] = types.get(e['type'], 0) + 1
        nchild += len(e.get('children', []))
    print(d['header'], '| events:', len(d['events']), '| children:', nchild, '|', types)
