"""Parallel Korean translation via codex exec.

Usage: translate_codex.py <job>  where job in {titles, abstracts, bios}
Reads job input JSON  (id -> english text), writes ko_<job>.json (id -> korean),
with resume support and validation + retry.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

JOB = sys.argv[1]
BATCH = {'titles': 80, 'abstracts': 6, 'bios': 6, 'misc': 45, 'pabs': 8, 'wtitles': 80, 'wabs': 8}[JOB]
WORKERS = int(os.environ.get('TR_WORKERS', '8'))
IN = f'tr_in_{JOB}.json'
OUT = f'ko_{JOB}.json'

PROMPTS = {
    'titles': (
        'You are a professional EN->KO translator for an ML conference (ICML) schedule app. '
        'Translate each English paper/talk title into natural, concise Korean. '
        'Keep technical terms, model names, benchmark names, and acronyms (LLM, RL, RLHF, SGD, etc.) in English as-is when that is how Korean ML researchers write them. '
        'Return ONLY a valid JSON object mapping each id to its Korean translation. No markdown fences, no commentary, no extra keys.'
    ),
    'abstracts': (
        'You are a professional EN->KO translator for an ML conference (ICML) schedule app. '
        'Each value below is an HTML fragment (event description). Translate the human-readable text into natural Korean, PRESERVING all HTML tags and structure exactly. '
        'Keep technical terms and acronyms in English where Korean ML researchers normally would. '
        'Return ONLY a valid JSON object mapping each id to the translated HTML string. No markdown fences, no commentary.'
    ),
    'bios': (
        'You are a professional EN->KO translator. Translate each speaker biography into natural Korean. '
        'Keep names, institutions, and award names in their common form (institution names may stay in English). '
        'Return ONLY a valid JSON object mapping each id to the Korean translation. No markdown fences, no commentary.'
    ),
    'pabs': (
        'You are a professional EN->KO translator for an ML conference (ICML) schedule app. '
        'Each value below is an HTML fragment (a paper abstract). Translate the text into natural Korean for ML researchers, PRESERVING all HTML tags exactly. '
        'Keep technical terms, method/model/benchmark names, and acronyms in English where Korean ML researchers normally would. Do not summarize; translate fully. '
        'Return ONLY a valid JSON object mapping each id to the translated HTML string. No markdown fences, no commentary.'
    ),
    'misc': (
        'You are a professional EN->KO translator for an ML conference (ICML) schedule app. '
        'Translate each short English string (event titles, session names, room names, labels) into natural, concise Korean. '
        'Keep proper nouns and acronyms sensible for Korean ML researchers (e.g. keep "LLM", model names in English). '
        'Return ONLY a valid JSON object mapping each id to the Korean translation. No markdown fences, no commentary.'
    ),
}

PROMPTS['wtitles'] = PROMPTS['titles']
PROMPTS['wabs'] = PROMPTS['pabs']

src = json.load(open(IN))
done = {}
if os.path.exists(OUT):
    done = json.load(open(OUT))
todo = {k: v for k, v in src.items() if k not in done or not done.get(k)}
print(f'{JOB}: {len(src)} total, {len(done)} done, {len(todo)} to translate', flush=True)

items = sorted(todo.items())
batches = [dict(items[i:i + BATCH]) for i in range(0, len(items), BATCH)]

lock = threading.Lock()
progress = {'n': 0}

def has_hangul(s):
    return bool(re.search(r'[가-힯]', s))

def run_batch(batch, tries=3):
    prompt = PROMPTS[JOB] + '\n\n' + json.dumps(batch, ensure_ascii=False)
    for attempt in range(tries):
        with tempfile.NamedTemporaryFile(mode='r', suffix='.txt', delete=False) as tf:
            outpath = tf.name
        try:
            cmd = ['codex', 'exec', '-s', 'read-only', '--skip-git-repo-check',
                   '-c', 'model_reasoning_effort="low"', '-o', outpath, '-']
            model = os.environ.get('TR_MODEL')
            if model:
                cmd[2:2] = ['-m', model]
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=900)
            raw = open(outpath).read().strip()
            # strip fences if any
            raw = re.sub(r'^```(json)?|```$', '', raw.strip(), flags=re.M).strip()
            m = re.search(r'\{.*\}', raw, re.S)
            if not m:
                raise ValueError('no json in output')
            res = json.loads(m.group(0))
            ok = {}
            for k, v in batch.items():
                t = res.get(k)
                if isinstance(t, str) and t.strip() and (has_hangul(t) or len(v) < 12):
                    ok[k] = t.strip()
            if len(ok) < len(batch) * 0.7 and attempt < tries - 1:
                raise ValueError(f'only {len(ok)}/{len(batch)} valid')
            return ok
        except Exception as e:
            if attempt == tries - 1:
                print('BATCH FAIL:', e, flush=True)
                return {}
        finally:
            try:
                os.unlink(outpath)
            except OSError:
                pass
    return {}

def save():
    json.dump(done, open(OUT, 'w'), ensure_ascii=False, indent=0)

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(run_batch, b): b for b in batches}
    for f in as_completed(futs):
        res = f.result()
        with lock:
            done.update(res)
            progress['n'] += 1
            save()
            print(f"batch {progress['n']}/{len(batches)} done, total translated {len(done)}/{len(src)}", flush=True)

save()
missing = [k for k in src if k not in done]
print(f'FINISHED {JOB}: {len(done)}/{len(src)} translated, missing {len(missing)}', flush=True)
if missing[:5]:
    print('missing sample:', missing[:5], flush=True)
