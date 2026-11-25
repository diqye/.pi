#!/usr/bin/env python3
"""Profile where the time went in a Claude Code agent session transcript (.jsonl).

Usage: profile_run.py TRANSCRIPT... -o OUTDIR [--episodes EPISODES.json] [--since ISO_UTC] [--until ISO_UTC]

Reads one or more Claude Code session transcripts (JSON lines), rebuilds the timeline of
runs (one run = one user prompt answered to the end of that turn), steps (tool calls) and
model time, classifies every tool call, and writes:

  OUTDIR/steps.csv      one row per tool call: run, start, model s, tool s, class, detail
  OUTDIR/runs.csv       one row per run: wall, model, tool, renders, looks, bytes, tokens
  OUTDIR/classes.csv    whole build by class of time (adds up to total run wall time)
  OUTDIR/episodes.csv   episodes with minutes, renders and marks
  OUTDIR/profile.json   everything above, for other tools

Time accounting. Every instant inside a run belongs to exactly one bucket:
  - tool time: at least one tool call is executing (from the moment the assistant message
    holding the call finished streaming to the moment its result was logged). When calls
    overlap, the interval is split equally between them.
  - model time: no tool executing; the agent is thinking or writing. It is charged to the
    next tool call it produced ("model time of that step"), or to "reply" when the run ends
    with text.
Time between runs (waiting for the next prompt) is excluded.

Episodes. With --episodes, a JSON list of {"first": step, "last": step, "label": str,
"mark": str} (step = global tool-call index printed in steps.csv) is used as given; labels
should quote the agent's own words. Without it, episodes are found automatically: steps are
cut into stretches at run boundaries and wherever the set of files touched stops
overlapping, and each stretch is labelled with the agent's first text in it and marked by
keyword. The automatic marks are a rough guide only.

Secrets: commands and texts are passed through a redaction filter and truncated to
200 characters before they are written anywhere.
"""
import argparse, csv, json, os, re, sys
from collections import defaultdict, Counter
from datetime import datetime, timezone

RED = re.compile(r'(sk-[A-Za-z0-9_-]{8,}|gh[pousr]_[A-Za-z0-9]{12,}|AKIA[0-9A-Z]{12,}|'
                 r'(api[_-]?key|token|passw(or)?d|secret|bearer|authorization)\S*\s*[:=]?\s*\S+)', re.I)


def clean(s, n=200):
    s = RED.sub('[redacted]', str(s).replace('\r', ' ').replace('\n', ' | '))
    return s[:n]


def ts(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()   # a time with no zone is UTC, as the logs are


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime('%H:%M:%S')


# ---------------------------------------------------------------- classification
IMG = re.compile(r'\.(png|jpe?g|gif|webp|bmp)$', re.I)
RENDER = re.compile(r'raea_run\.py|\$R\s+\S+\.tsx|\braea\s+(render|still)\b')
WAIT = re.compile(r'tasklist|Get-CimInstance|Get-Process|pgrep|(?:^|[;&|]\s*)sleep\s|t3_background_wait', re.I)
SOUND = re.compile(r'make_sound|loudnorm|ebur128|volumedetect|astats|\.wav\b|sound/|\braea sounds\b|'
                   r'-af\b|afade|amix|faster_whisper|music\.ts|\.mp3', re.I)   # \bE2\b (a pitch in the evening build) matched a film folder named E2
DELIVER = re.compile(r'\braea check\b(?!\s+--help)|measure_film|sheet\.py|word_times|libx264|'
                     r'scale-compare|share\.mp4|key-\w+\.png|date \+%H|--time-style|first-frames', re.I)
DIAG = re.compile(r'signalstats|render\.json|import math', re.I)
EDIT = re.compile(r"sed -i|open\([^)]*['\"]w['\"]|\.write\(|cat >(?!>)\s*\S+\.(tsx?|py|js|json|md)|"
                  r"cat > \S+ <<|> \S+\.(tsx?|py|json)\b|tee\b|\bcp\b[^|;&]*\.tsx\b|\brm\b", re.I)
READCMD = re.compile(r'\b(cat|grep|sed -n|head|tail|ls|wc|find|which|strings|raea guide|--help|'
                     r'ffprobe|file)\b')
SHEET_SELF = re.compile(r'tile=|-sheet\.jpg|hstack|vstack|xstack')


def render_kind(cmd):
    """Return (kind, count) for raea renders in a command: kind in film/clip/still."""
    kinds = []
    for m in re.finditer(r'(raea_run\.py|\$R\b|\braea\s+(?:render|still)\b)([^\n|;&]*)', cmd):
        args = m.group(2)
        if '--help' in args or not re.search(r'\.tsx', args):
            continue
        if re.search(r'--at\b|--frame\s', args):
            kinds.append('still')
        elif re.search(r'--frames\b', args):
            kinds.append('clip')
        else:
            comp = re.search(r'--composition\s+(\S+)', args)
            out = re.search(r'-o\s+(\S+)', args)
            outp = out.group(1) if out else ''
            if comp is None or comp.group(1) in ('film', 'main', 'Main', 'Film') or \
                    re.search(r'film|master|png\d+|\$S', outp):
                kinds.append('film')
            else:
                kinds.append('clip')
    if not kinds:
        return None, 0
    for k in ('film', 'clip', 'still'):
        if k in kinds:
            return k, len(kinds)


def classify(name, inp):
    """Return (class, subclass, bytes_written, bytes_read_hint, files)."""
    inp = inp or {}
    files = []
    if name == 'Read':
        p = inp.get('file_path', '')
        files.append(p)
        if IMG.search(p):
            return 'look', '', 0, files
        return 'read', '', 0, files
    if name in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        p = inp.get('file_path', '') or inp.get('notebook_path', '')
        files.append(p)
        if name == 'Write':
            b = len((inp.get('content') or '').encode('utf8'))
        elif name == 'MultiEdit':
            b = sum(len((e.get('new_string') or '').encode('utf8')) for e in inp.get('edits', []))
        else:
            b = len((inp.get('new_string') or inp.get('new_source') or '').encode('utf8'))
        if re.search(r'\.(md|txt)$', p, re.I):
            return 'deliver', 'notes', b, files
        return 'write', '', b, files
    if name in ('Grep', 'Glob'):
        return 'read', '', 0, files
    if name == 'Bash':
        cmd = inp.get('command', '')
        files += re.findall(r'[\w./-]+\.(?:tsx|ts|py|md|json|png|jpg|mp4|wav)\b', cmd)
        b = len(cmd.encode('utf8')) if EDIT.search(cmd) else 0
        if WAIT.search(cmd) and not RENDER.search(cmd):
            return 'wait', '', 0, files
        k, n = render_kind(cmd)
        if k:
            return 'render', k, b, files
        vd = re.search(r'(?:vd(?:\.py)?|\$\{?[Vv][Dd]\}?)"?\s+(look|sound|export|render)\b|look\.py', cmd)   # "$VD" look too
        if vd:   # the skill's own commands that render through the queue
            return 'render', 'film' if vd.group(1) == 'export' else 'still', b, files
        if re.search(r'make_sound|loudnorm|ebur128|\braea sounds\b', cmd) or \
                (SOUND.search(cmd) and not DELIVER.search(cmd)):
            return 'sound', '', b, files
        if SHEET_SELF.search(cmd) and not re.search(r'sheet\.py', cmd):
            return 'look', 'sheet', b, files
        if DELIVER.search(cmd):
            return 'deliver', '', b, files
        if DIAG.search(cmd):
            return 'other', 'diagnose', b, files
        if b:
            return 'write', 'shell', b, files
        if READCMD.search(cmd):
            return 'read', 'shell', 0, files
        return 'other', '', 0, files
    if 'background_wait' in name or name in ('TaskOutput',):
        return 'wait', '', 0, files
    if name in ('Agent', 'Task', 'SendMessage') or re.search(r'delegate|t3_thread|task_status', name or ''):
        return 'agents', '', 0, files
    return 'other', '', 0, files


# ---------------------------------------------------------------- loading
BG_DONE = {}          # background task id -> when its notification said it completed with exit code 0
NOT_CLASSED_BY = {}   # step kind -> seconds of the not-classed time, so the split says what that time was


def local(t):
    """A time on this machine's clock, as the maker saw it (the logs are UTC)."""
    return datetime.fromtimestamp(t).astimezone().strftime('%H:%M:%S')


def zone():
    now = datetime.now().astimezone()
    off = now.utcoffset().total_seconds() / 3600
    return f"{now.tzname()}, UTC{off:+.0f}"


def human_prompt(e):
    if e.get('type') != 'user' or e.get('isMeta'):
        return None
    c = (e.get('message') or {}).get('content')
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        if any(isinstance(x, dict) and x.get('type') == 'tool_result' for x in c):
            return None
        t = ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
        if t.startswith('[Image') or t.startswith('[Request interrupted'):
            return None
        return t
    return None


def load(paths, until=None, since=None):
    ents = []
    for p in paths:
        with open(p, encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if not e.get('timestamp') or e.get('type') not in ('user', 'assistant'):
                    continue
                if e.get('isSidechain'):
                    continue
                t = ts(e['timestamp'])
                if until and t > until:
                    continue
                if since and t < since:
                    continue
                e['_t'] = t
                ents.append(e)
    ents.sort(key=lambda e: e['_t'])
    return ents


def build(ents):
    calls = {}          # id -> dict
    order = []
    msgs = {}           # message id -> usage, t
    texts = []          # (t, text)
    prompts = []        # (t, text, starts_run)
    last_stop = 'end_turn'
    msg_last_t = {}     # message id -> last entry time (end of streaming)
    for e in ents:
        m = e.get('message') or {}
        if e['type'] == 'assistant':
            mid = m.get('id') or e.get('uuid')
            msg_last_t[mid] = e['_t']
            if m.get('usage'):
                msgs[mid] = (m['usage'], e['_t'])
            last_stop = m.get('stop_reason') or last_stop
            for c in m.get('content') or []:
                if not isinstance(c, dict):
                    continue
                if c.get('type') == 'tool_use':
                    cl, sub, b, files = classify(c.get('name'), c.get('input'))
                    calls[c['id']] = dict(id=c['id'], name=c.get('name'), input=c.get('input') or {},
                                          t_emit=e['_t'], mid=mid, cls=cl, sub=sub, bytes=b,
                                          files=files, t_res=None, res='')
                    order.append(c['id'])
                elif c.get('type') == 'text' and c.get('text', '').strip():
                    texts.append((e['_t'], c['text']))
        else:
            raw = m.get('content')
            raw = raw if isinstance(raw, str) else ' '.join(x.get('text', '') for x in raw if isinstance(x, dict)) if isinstance(raw, list) else ''
            if '<task-notification>' in raw:
                tid = re.search(r'<task-id>(\w+)</task-id>', raw)
                if tid and '<status>completed</status>' in raw and 'exit code 0' in raw:
                    BG_DONE[tid.group(1)] = e['_t']
            hp = human_prompt(e)
            if hp is not None:
                prompts.append((e['_t'], hp, last_stop == 'end_turn'))
                continue
            c = m.get('content')
            if isinstance(c, list):
                for x in c:
                    if isinstance(x, dict) and x.get('type') == 'tool_result' and x.get('tool_use_id') in calls:
                        cc = x.get('content')
                        if isinstance(cc, list):
                            cc = ' '.join(y.get('text', '') for y in cc if isinstance(y, dict))
                        k = calls[x['tool_use_id']]
                        k['t_res'] = e['_t']
                        k['res'] = str(cc or '')
                        k['is_error'] = bool(x.get('is_error'))
    # a call starts executing when its whole assistant message has finished streaming
    for k in calls.values():
        k['t_start'] = max(k['t_emit'], msg_last_t.get(k['mid'], k['t_emit']))
    return calls, order, msgs, texts, prompts, ents


def runs_from(prompts, ents, calls, order, since=None):
    starts = [p for p in prompts if p[2]]
    # a window opened with --since usually falls inside a turn: its first entries belong to no prompt, so a run starts
    # at the first of them; without it a film made mid-session would be profiled as nothing
    if since is not None and ents and (not starts or ents[0]['_t'] < starts[0][0]):
        starts = [(ents[0]['_t'], '(from --since, inside a turn)', True)] + starts
    runs = []
    last_t = ents[-1]['_t']
    ass_t = [e['_t'] for e in ents if e['type'] == 'assistant'] + \
            [k['t_res'] for k in calls.values() if k['t_res']]
    ass_t.sort()
    for i, (t0, txt, _) in enumerate(starts):
        t_next = starts[i + 1][0] if i + 1 < len(starts) else float('inf')
        inside = [t for t in ass_t if t0 <= t < t_next]
        t1 = max(inside) if inside else t0
        runs.append(dict(n=i + 1, t0=t0, t1=t1, prompt=txt))
    return runs


def run_of(runs, t):
    for r in runs:
        if r['t0'] <= t <= r['t1'] + 1e-6:
            return r['n']
    return None


def account(runs, calls, order):
    """Interval walk: split each run's wall time into tool time per call and model time."""
    for k in calls.values():
        k['tool_s'] = 0.0
        k['model_s'] = 0.0
    reply = defaultdict(float)
    for r in runs:
        evs = {r['t0'], r['t1']}
        cs = [calls[i] for i in order if r['t0'] <= calls[i]['t_emit'] <= r['t1']]
        for k in cs:
            evs.add(min(max(k['t_start'], r['t0']), r['t1']))
            if k['t_res']:
                evs.add(min(k['t_res'], r['t1']))
        evs = sorted(evs)
        for a, b in zip(evs, evs[1:]):
            if b <= a:
                continue
            mid = (a + b) / 2
            running = [k for k in cs if k['t_start'] <= mid and (k['t_res'] or r['t1'] + 1) > mid]
            if running:
                for k in running:
                    k['tool_s'] += (b - a) / len(running)
            else:
                nxt = [k for k in cs if k['t_emit'] >= b - 1e-6]
                if nxt:
                    min(nxt, key=lambda k: k['t_emit'])['model_s'] += b - a
                else:
                    reply[r['n']] += b - a
    return reply


REAL = re.compile(r'real\s+(\d+)m([\d.]+)s')


def tokens_by_run(msgs, runs):
    out = defaultdict(lambda: Counter())
    for mid, (u, t) in msgs.items():
        n = run_of(runs, t)
        if n is None:
            continue
        c = out[n]
        c['input'] += u.get('input_tokens') or 0
        c['cache_read'] += u.get('cache_read_input_tokens') or 0
        c['cache_write'] += u.get('cache_creation_input_tokens') or 0
        c['output'] += u.get('output_tokens') or 0
        c['thinking'] += (u.get('output_tokens_details') or {}).get('thinking_tokens') or 0
        c['messages'] += 1
    return out


# ---------------------------------------------------------------- episodes
MARKS = {
    'engine': 'engine silent or surprising',
    'drawing': 'drawing or layout by eye',
    'timing': 'timing or animation',
    'sound': 'sound',
    'director': 'director request carried out',
    'reporting': 'reporting',
    'wait': 'waiting on another job (machine busy)',
    'setup': 'reading in (not an episode)',
}


def auto_mark(text):
    t = text.lower()
    if re.search(r"draws? nothing|doesn't draw|don't draw|won't draw|not drawn|vanish|refus|no effect|"
                 r"silently|missing|ran out|false positive|unexplained|didn't decode", t):
        return 'engine'
    if re.search(r'notes\.md|report', t):
        return 'reporting'
    if re.search(r'compile|cargo|waiting', t):
        return 'wait'
    if re.search(r'sound|thunder|rain|music|\bdb\b|lufs|mix', t):
        return 'sound'
    if re.search(r'timing|clip|dive|camera|move|motion|push|cut', t):
        return 'timing'
    if re.search(r'draw|frame|shot|layout|colou?r|light|scene|still|look', t):
        return 'drawing'
    return 'not classed'


def auto_episodes(order, calls, texts):
    eps, cur, cur_files, cur_run = [], [], set(), None
    for i, cid in enumerate(order):
        k = calls[cid]
        fs = {os.path.basename(f) for f in k['files'] if f}
        if cur and (k['run'] != cur_run or (fs and cur_files and not (fs & cur_files) and len(cur) > 2)):
            eps.append(cur)
            cur, cur_files = [], set()
        cur.append(i)
        cur_files |= fs
        cur_run = k['run']
    if cur:
        eps.append(cur)
    out = []
    for e in eps:
        t0 = calls[order[e[0]]]['t_emit']
        t1 = calls[order[e[-1]]]['t_res'] or t0
        lab = next((x for t, x in texts if t0 - 60 <= t <= t1), '')
        ks = [calls[order[i]] for i in e]
        pages = sum(1 for k in ks if k['cls'] in ('read', 'deliver', 'write') and any(str(f).lower().endswith('.md') for f in k['files']))
        if sum(1 for k in ks if k['cls'] == 'agents') * 2 >= len(ks):
            mark = 'agents'                       # writers, readers, a director: other agents working, not this one drawing
        elif pages * 2 >= len(ks):
            mark = 'pages'                        # reading and writing pages: briefs, notes, readings
        else:
            mark = auto_mark(lab)
        out.append(dict(first=e[0], last=e[-1], label=clean(lab, 160), mark=mark))
    return out


QUEUE_LINE = re.compile(r"queue: waiting (\d+) s; held by [^\n|]*")
LOOK_LINE = re.compile(r"LOOK \S+ \S+ \d+ tiles\s+total [\d.]+s \(queue ([\d.]+)s, raea [\d.]+s")
HEAVY_LINE = re.compile(r"heavy\.py: scheduled;[^\n|]*\(waited (\d+) s\)")


def first_full_render(order, calls):
    """When the first full render's result came back. Full is read from the invocation, not a frame count: a render of
    the film's own composition (render_kind's 'film': no --at, --frame or --frames, composition film or main), or vd
    export's own "picture rendered once". A range (composition range) or a clip of any length is not one; a short whole
    film is. A film render run in the background reports in a later step (the read of its output): that step counts when
    the output it names is the one a film render was asked to write."""
    films = set()
    for cid in order:
        k = calls[cid]
        res = k.get('res') or ''
        if k['cls'] == 'render' and k['sub'] == 'film':
            m = re.search(r"-o\s+(\S+)", (k.get('input') or {}).get('command', ''))
            if m:
                films.add(os.path.basename(m.group(1).strip('"\'').rstrip('/\\')))
            if re.search(r"APPLIED|frames rendered to", res) and not re.search(r"FAILED|REFUSED", res):
                return k['t_res'] or k['t_emit']
            # run in the background (Round's first `vd export`): it ends when its notification says it completed
            bg = re.search(r"running in background with ID: (\w+)", res)
            if bg and bg.group(1) in BG_DONE:
                return BG_DONE[bg.group(1)]
        if "picture rendered once" in res:
            return k['t_res'] or k['t_emit']
        for m in re.finditer(r"frames rendered to (\S+)", res):
            if os.path.basename(m.group(1).rstrip('/\\')) in films:
                return k['t_res'] or k['t_emit']
    return None


def queue_seconds(res, seen):
    """Render-queue seconds a step's output reports (raea_run's "queue: waiting N s", look's "queue X s"), counting each
    printed line once across the session (a maker may read one output file several times)."""
    q, prev = 0.0, None
    for m in QUEUE_LINE.finditer(res):
        line, n = m.group(0), int(m.group(1))
        if line in seen:
            prev = n
            continue
        seen.add(line)
        if prev is not None and n > prev:
            q += n - prev
        prev = n
    for m in LOOK_LINE.finditer(res):
        if m.group(0) not in seen:
            seen.add(m.group(0))
            q += float(m.group(1))
    return q


def split(order, calls, eps, cls, total_s):
    """Minutes in exclusive classes that add up to the total: each step's seconds (its tool time and the thinking that led
    to it) go to one class. Out of a step first come the render-queue and heavy-job seconds its own output reports
    (raea_run's, look's and heavy.py's lines; waits printed with no length can't be counted, so a lower bound), then a
    look's whole step is looking, then the rest goes by the episode's mark: making or rework (either side of the first full
    render), engine faults, reporting, other agents, pages, other waiting, not classed. Final replies are their own class."""
    of_step = {}
    for e in eps:
        for i in range(e['first'], e['last'] + 1):
            of_step[i] = e['mark']
    cut = first_full_render(order, calls)
    out = dict.fromkeys(("making", "rework", "looking", "render_queue", "heavy_job", "engine", "reporting", "agents", "pages",
                         "waiting_other", "not_classed"), 0.0)
    # the waits the tools printed, wherever they were read (a background render's output is read in a later, short step);
    # they happened while the maker waited, so they are taken out of the wait and render steps' time, earliest first
    seen, queue, heavy = set(), 0.0, 0.0
    for cid in order:
        res = calls[cid].get('res') or ''
        queue += queue_seconds(res, seen)
        heavy += max((int(m.group(1)) for m in HEAVY_LINE.finditer(res)), default=0)
    taken = {}
    for i, cid in enumerate(order):
        k = calls[cid]
        if k['cls'] in ('wait', 'render') and (queue > 0 or heavy > 0):
            room = k['tool_s'] + k['model_s']
            q = min(room, queue)
            h = min(room - q, heavy)
            queue, heavy = queue - q, heavy - h
            taken[i] = (q, h)
    unplaced = queue + heavy
    for i, cid in enumerate(order):
        k = calls[cid]
        q, h = taken.get(i, (0.0, 0.0))
        out['render_queue'] += q
        out['heavy_job'] += h
        rest = k['tool_s'] + k['model_s'] - q - h
        mark = of_step.get(i, 'not classed')
        if k['cls'] == 'look':
            out['looking'] += rest
        elif mark in ('drawing', 'timing', 'sound'):
            out['making' if cut is None or k['t_emit'] < cut else 'rework'] += rest
        elif mark in ('engine', 'reporting', 'agents', 'pages'):
            out[mark] += rest
        elif mark == 'wait':
            out['waiting_other'] += rest
        elif k['cls'] in ('write', 'render', 'sound'):
            # writing the film's source, drawing it or making its sound is making, whatever words were near it: Round's
            # Write of film.tsx counted as "not classed" because its episode had no keyword
            out['making' if cut is None or k['t_emit'] < cut else 'rework'] += rest
        else:
            out['not_classed'] += rest
            NOT_CLASSED_BY[k['cls'] or 'other'] = NOT_CLASSED_BY.get(k['cls'] or 'other', 0.0) + rest
    out = {k: v / 60 for k, v in out.items()}
    out['replies'] = max(0.0, total_s / 60 - sum(out.values()))
    out['total'] = total_s / 60
    out['first_full_render_min'] = (cut - calls[order[0]]['t_emit']) / 60 if cut and order else None
    out['queue_not_placed'] = unplaced / 60   # waits reported beyond the session's wait and render time: not in the classes
    return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in out.items()}


def episode_stats(ep, order, calls):
    ks = [calls[order[i]] for i in range(ep['first'], ep['last'] + 1)]
    secs = sum(k['tool_s'] + k['model_s'] for k in ks)
    rend = [k for k in ks if k['cls'] == 'render']
    return dict(ep, start=iso(ks[0]['t_emit'] - ks[0]['model_s']), minutes=secs / 60,
                renders=sum(k['n_render'] for k in rend), render_min=sum(k['tool_s'] for k in rend) / 60,
                looks=sum(1 for k in ks if k['cls'] == 'look'), run=ks[0]['run'], steps=len(ks))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('transcripts', nargs='+')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--episodes')
    ap.add_argument('--since', help='ignore entries before this UTC time (ISO); a window that opens inside a turn starts a run there')
    ap.add_argument('--until', help='ignore entries after this UTC time (ISO)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    until = ts(a.until) if a.until else None
    since = ts(a.since) if a.since else None
    ents = load(a.transcripts, until, since)
    if not ents:
        raise SystemExit('no entries in that window')
    calls, order, msgs, texts, prompts, ents = build(ents)
    runs = runs_from(prompts, ents, calls, order, since)
    for k in calls.values():
        k['run'] = run_of(runs, k['t_emit'])
        # a step classed render renders at least once: the skill's own vd look and vd export name no raea output
        # frames, so one film's profile said "renders 0 (1343s)", no renders and 22 minutes of them in one line
        k['n_render'] = max(1, render_kind(k['input'].get('command', ''))[1]) if k['cls'] == 'render' else 0
        m = REAL.findall(k['res'] or '')
        k['timed_s'] = sum(int(x) * 60 + float(y) for x, y in m)
    reply = account(runs, calls, order)
    tok = tokens_by_run(msgs, runs)

    # steps.csv
    with open(os.path.join(a.out, 'steps.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.writer(f)
        w.writerow(['step', 'run', 'start_utc', 'model_s', 'tool_s', 'tool', 'class', 'sub', 'renders',
                    'bytes_written', 'timed_real_s', 'error', 'detail'])
        for i, cid in enumerate(order):
            k = calls[cid]
            inp = k['input']
            det = inp.get('command') or inp.get('file_path') or json.dumps(inp)
            w.writerow([i, k['run'], iso(k['t_emit']), round(k['model_s'], 1), round(k['tool_s'], 1),
                        k['name'], k['cls'], k['sub'], k['n_render'], k['bytes'], round(k['timed_s'], 1),
                        int(k.get('is_error', False)), clean(det, 200)])

    # runs
    rows = []
    for r in runs:
        ks = [calls[c] for c in order if calls[c]['run'] == r['n']]
        rend = [k for k in ks if k['cls'] == 'render']
        t = tok.get(r['n'], Counter())
        rows.append(dict(run=r['n'], start=iso(r['t0']), end=iso(r['t1']), start_l=local(r['t0']), end_l=local(r['t1']), wall_min=(r['t1'] - r['t0']) / 60,
                         model_min=(sum(k['model_s'] for k in ks) + reply[r['n']]) / 60,
                         tool_min=sum(k['tool_s'] for k in ks) / 60, steps=len(ks),
                         renders=sum(k['n_render'] for k in rend), render_s=sum(k['tool_s'] for k in rend),
                         looks=sum(1 for k in ks if k['cls'] == 'look'),
                         bytes_written=sum(k['bytes'] for k in ks),
                         tok_in=t['input'], tok_cache_read=t['cache_read'], tok_cache_write=t['cache_write'],
                         tok_out=t['output'], tok_thinking=t['thinking'], api_messages=t['messages'],
                         prompt=clean(r['prompt'], 120)))
    with open(os.path.join(a.out, 'runs.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # classes
    cls = defaultdict(lambda: dict(n=0, tool_s=0.0, model_s=0.0, bytes=0, renders=0))
    for k in calls.values():
        if k['run'] is None:
            continue
        key = k['cls'] + (':' + k['sub'] if k['cls'] == 'render' else '')
        c = cls[key]
        c['n'] += 1
        c['tool_s'] += k['tool_s']
        c['model_s'] += k['model_s']
        c['bytes'] += k['bytes']
        c['renders'] += k['n_render']
    cls['reply (final text)']['model_s'] += sum(reply.values())
    # alternative view: model time charged to the step BEFORE it (time spent digesting a result)
    after = defaultdict(float)
    prev = {}
    for cid in order:
        k = calls[cid]
        if k['run'] is None:
            continue
        key = k['cls'] + (':' + k['sub'] if k['cls'] == 'render' else '')
        after[prev.get(k['run'], 'prompt (reading the brief)')] += k['model_s']
        prev[k['run']] = key
    for n, s in reply.items():
        after[prev.get(n, 'prompt (reading the brief)')] += s
    total = sum(r['t1'] - r['t0'] for r in runs)
    with open(os.path.join(a.out, 'classes.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.writer(f)
        w.writerow(['class', 'calls', 'renders', 'tool_min', 'model_min', 'total_min', 'share', 'bytes',
                    'model_after_min'])
        keys = set(cls) | set(after)
        for key in sorted(keys, key=lambda kk: -(cls[kk]['tool_s'] + cls[kk]['model_s'])):
            c = cls[key]
            s = c['tool_s'] + c['model_s']
            w.writerow([key, c['n'], c['renders'], round(c['tool_s'] / 60, 2), round(c['model_s'] / 60, 2),
                        round(s / 60, 2), round(s / total, 4), c['bytes'], round(after[key] / 60, 2)])
        w.writerow(['TOTAL', len(order), '', '', '', round(total / 60, 2), 1.0, ''])

    # episodes
    eps = json.load(open(a.episodes, encoding='utf8')) if a.episodes else auto_episodes(order, calls, texts)
    eps = [episode_stats(e, order, calls) for e in eps]
    with open(os.path.join(a.out, 'episodes.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.writer(f)
        w.writerow(['first', 'last', 'run', 'start_utc', 'minutes', 'renders', 'render_min', 'looks', 'mark', 'label'])
        for e in eps:
            w.writerow([e['first'], e['last'], e['run'], e['start'], round(e['minutes'], 2), e['renders'],
                        round(e['render_min'], 2), e['looks'], e['mark'], e['label']])
    by_mark = defaultdict(float)
    for e in eps:
        by_mark[e['mark']] += e['minutes']
    sp = split(order, calls, eps, cls, total)
    json.dump(dict(runs=rows, classes={k: v for k, v in cls.items()}, total_min=total / 60,
                   episodes=eps, by_mark=by_mark, reply_s=reply, split=sp,
                   texts=[(iso(t), clean(x, 200)) for t, x in texts]),
              open(os.path.join(a.out, 'profile.json'), 'w', encoding='utf8'), indent=1, default=str)
    print('runs', len(runs), 'steps', len(order), 'total min %.1f' % (total / 60))
    for r in rows:
        print('run %d %s-%s wall %.1f model %.1f tool %.1f renders %d (%.0fs) looks %d out %d' % (
            r['run'], r['start_l'], r['end_l'], r['wall_min'], r['model_min'], r['tool_min'], r['renders'],
            r['render_s'], r['looks'], r['tok_out']))
    print(f'run times are this machine\'s clock ({zone()}); the CSV files keep UTC')
    print('by mark:', {k: round(v, 1) for k, v in by_mark.items()})
    print('split (min): ' + ', '.join(f"{k.replace('_', ' ')} {v}" for k, v in sp.items() if v is not None)
          + ' (the render queue counts only waits the tools printed with a length: a lower bound)')
    if NOT_CLASSED_BY:
        print('not classed, by kind of step, largest first (min): '
              + ', '.join(f"{k} {v / 60:.1f}" for k, v in sorted(NOT_CLASSED_BY.items(), key=lambda kv: -kv[1])))
    launched = sum(1 for k in calls.values() if k['cls'] == 'agents')
    if launched:
        print(f'agents: {launched} steps launched or waited on other agents; "other agents" counts only that time in this '
              'session. Reader and writer agents\' own minutes are in their own logs and are not counted here.')


if __name__ == '__main__':
    import utf8  # noqa: F401
    main()
