"""Build translation input files from schedule + events + papers."""
import json

sched = json.load(open('schedule_raw.json'))
events = json.load(open('events_detail.json'))
papers = json.load(open('papers.json'))['results']
by_title = {}
by_id = {}
for r in papers:
    by_title.setdefault(r['name'].strip().lower(), r)
    by_id[str(r['id'])] = r

# 1) paper titles (posters with ids + orals matched by title)
titles = {}
for day in sched['days']:
    for e in day['events']:
        for c in e.get('children', []):
            if c.get('id'):
                titles[c['id']] = c['title']
            else:
                rec = by_title.get(c['title'].strip().lower())
                if rec:
                    titles[str(rec['id'])] = rec['name']
json.dump(titles, open('tr_in_titles.json', 'w'), ensure_ascii=False, indent=0)

# 2) event abstracts (HTML)
abstracts = {}
for eid, d in events.items():
    if d.get('abstract_html'):
        abstracts[eid] = d['abstract_html']
json.dump(abstracts, open('tr_in_abstracts.json', 'w'), ensure_ascii=False, indent=0)

# 3) speaker bios
bios = {}
for eid, d in events.items():
    for i, sp in enumerate(d.get('speakers', [])):
        if sp.get('bio'):
            bios[f'{eid}:{i}'] = sp['bio']
json.dump(bios, open('tr_in_bios.json', 'w'), ensure_ascii=False, indent=0)

# 4) misc short strings: event titles, session titles, headers, rooms
misc = {}
def add(key, val):
    if val:
        misc[key] = val
for day in sched['days']:
    for e in day['events']:
        add(f"t:{e['id']}", e['title'])
rooms = set()
for day in sched['days']:
    for e in day['events']:
        if e.get('room'):
            rooms.add(e['room'])
for eid, d in events.items():
    if d.get('room'):
        rooms.add(d['room'])
for i, r in enumerate(sorted(rooms)):
    add(f'room:{r}', r)
json.dump(misc, open('tr_in_misc.json', 'w'), ensure_ascii=False, indent=0)

print('titles:', len(titles), '| abstracts:', len(abstracts), '| bios:', len(bios), '| misc:', len(misc))
import statistics
alens = [len(v) for v in abstracts.values()]
print('abstract chars total:', sum(alens), 'median:', statistics.median(alens) if alens else 0)
print('title chars total:', sum(len(v) for v in titles.values()))
