"""Tables from Saved/Logs/ford_diag.log (Art/ford_diag.bat, FGTFordDiagRunner, gt.Water.Diag). Diagnostic only.

    python Art/tools/ford_diag.py [log] [--rows DIR]

Prints, per ford run: entry/exit speed and time, the minimum speed in the water and where, equilibrium stretches
(speed within 0.1 m/s for >= 1 s), the force budget at the slowest point and every 2 m through the water, the peak slip
ratio, the exit-bank dynamics (+-4 m), the front wheels' sinkage/radius change, and the bow wave in the last 2 m of
water; then the terrain profile numbers and the rocks. --rows DIR also writes each run's 0.1 s exit-bank rows there.
"""
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:]]
rows_dir = None
if '--rows' in args:
    i = args.index('--rows')
    rows_dir = args[i + 1]
    del args[i:i + 2]
LOG = args[0] if args else os.path.join(HERE, '..', '..', 'Saved', 'Logs', 'ford_diag.log')
lines = open(LOG, encoding='utf-8', errors='replace').read().splitlines()

G = 9.8


def kv(segment):
    out = {}
    for tok in segment.split():
        if '=' in tok:
            k, v = tok.split('=', 1)
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def parse_diag(text):
    parts = text.split(' | ')
    s = kv(parts[0])
    s['w'] = []
    for p in parts[1:]:
        head, _, rest = p.partition(' ')
        s['w'].append(kv(rest))
    return s


fords, prof, runs, rocks, surf = {}, {}, {}, [], {}
cur = None
mass = None
re_ford = re.compile(r'GTFORDDIAG (ford\w): section \d+ ([\d.]+)-([\d.]+) m depth ([\d.]+) m; sheet \S+ level ([-\d.]+) cm; .* entry ([-\d.]+) exit ([-\d.]+)')
re_prof = re.compile(r'GTFORDPROF (\w+) a=([-\d.]+) level=([-\d.]+) c=(\S+) l=(\S+) r=(\S+)')
re_go = re.compile(r'GTFORDDIAG run (\S+) go at t=([\d.]+)')
re_start = re.compile(r'GTFORDDIAG run (\S+) start: .* arc ([-\d.]+);')
re_end = re.compile(r'GTFORDDIAG end (\S+): ([^;]+);')
re_rock = re.compile(r'rock (\d+) at \(([-\d.]+), ([-\d.]+)\) m size ([\d.]+) m: arc ([-\d.]+) offset ([-+\d.]+) m \((\w+): ([-+\d.]+) m from the entry waterline, ([-+\d.]+) m from the exit\); top ([-\d.]+) cm')
re_surf = re.compile(r'GTFORDDIAG (ford\w) surface line (\w) \(offset ([-+\d.]+) m\) changes: (.*)$')
re_mass = re.compile(r'the car on the pad: mass ([\d.]+) kg')
starts = {}
dry_end = {}
re_dry = re.compile(r'GTFORDDIAG end (dry\w*): through; (.*); mean frame')
for line in lines:
    m = re_dry.search(line)
    if m:
        dry_end[m.group(1)] = m.group(2)
    if 'GTWATERDIAG ' in line:
        if cur is not None:
            runs[cur]['s'].append(parse_diag(line.split('GTWATERDIAG ', 1)[1]))
        continue
    m = re_prof.search(line)
    if m:
        f = m.group(1)
        row = {'a': float(m.group(2)), 'level': float(m.group(3))}
        for key, g in (('c', 4), ('l', 5), ('r', 6)):
            p = m.group(g).split(',')
            row[key] = (float(p[0]), float(p[1]), float(p[2]), p[3], p[4])
        prof.setdefault(f, []).append(row)
        continue
    m = re_ford.search(line)
    if m:
        fords[m.group(1)] = dict(start=float(m.group(2)), end=float(m.group(3)), depth=float(m.group(4)), level=float(m.group(5)),
                                 entry=float(m.group(6)), exit=float(m.group(7)))
        continue
    m = re_surf.search(line)
    if m:
        surf.setdefault(m.group(1), {})[m.group(2)] = m.group(4)
        continue
    m = re_mass.search(line)
    if m:
        mass = float(m.group(1))
        continue
    m = re_start.search(line)
    if m:
        starts[m.group(1)] = float(m.group(2))
        continue
    m = re_go.search(line)
    if m:
        cur = m.group(1)
        runs[cur] = {'go': float(m.group(2)), 's': [], 'why': '', 'startarc': starts.get(cur, 0.0)}
        continue
    m = re_end.search(line)
    if m:
        if m.group(1) in runs:
            runs[m.group(1)]['why'] = m.group(2)
        cur = None
        continue
    m = re_rock.search(line)
    if m:
        rocks.append(dict(i=int(m.group(1)), x=float(m.group(2)), y=float(m.group(3)), size=float(m.group(4)), arc=float(m.group(5)),
                          off=float(m.group(6)), ford=m.group(7), rel_entry=float(m.group(8)), rel_exit=float(m.group(9)), top=float(m.group(10))))
mass = mass or 2100.0


def every(samples, dt=0.1):
    out, last = [], -1e9
    for s in samples:
        if s['t'] >= last + dt - 0.0005:
            out.append(s)
            last = s['t']
    return out


def accel(series, i):
    j0, j1 = max(0, i - 2), min(len(series) - 1, i + 2)
    dt = series[j1]['t'] - series[j0]['t']
    return (series[j1]['v'] - series[j0]['v']) / dt if dt > 0 else 0.0


def budget(s, a):
    w = s['w']
    scale = s['weightN'] / 4.0
    surfN = sum(x['sd'] for x in w if x['c'] == 1) * scale
    ploughN = sum(x['pd'] for x in w if x['c'] == 1) * scale
    bellyN = sum(x['bd'] for x in w if x['c'] == 1) * scale
    grade = mass * G * math.sin(math.radians(s['pitch']))
    resid = s['tracN'] - s['rollN'] - s['hullAlongN'] - grade - mass * a
    return dict(trac=s['tracN'], cap=s['capN'], roll=s['rollN'], water=s['waterN'], waterRaw=s['waterRawN'], mud=s['rollN'] - s['waterN'],
                surf=surfN, plough=ploughN, belly=bellyN, hull=s['hullAlongN'], lift=s['liftN'], spring=s['springN'], load=s['loadN'],
                weight=s['weightN'], grade=grade, ma=mass * a, resid=resid)


def fmt_budget(b):
    return ('tractive %.0f (grip cap %.0f) | rolling total %.0f = water %.0f (uncapped %.0f) + mud/surface %.0f [surface %.0f plough %.0f belly %.0f, uncapped] | '
            'hull drag %.0f | hull lift %.0f | springs %.0f + lift = %.0f vs weight %.0f (loads sum %.0f) | grade %.0f | m*a %.0f | unexplained %.0f'
            % (b['trac'], b['cap'], b['roll'], b['water'], b['waterRaw'], b['mud'], b['surf'], b['plough'], b['belly'], b['hull'], b['lift'],
               b['spring'], b['spring'] + b['lift'], b['weight'], b['load'], b['grade'], b['ma'], b['resid']))


print('== ford diagnostic: %s' % os.path.abspath(LOG))
print('car mass %.0f kg; fords: %s' % (mass, ', '.join('%s level %.1f cm, entry %.2f exit %.2f, section %.2f-%.2f' % (k, f['level'], f['entry'], f['exit'], f['start'], f['end']) for k, f in fords.items())))
for k, v in surf.items():
    print('  %s surface changes: %s' % (k, ' || '.join('%s: %s' % (a, b) for a, b in v.items())))

summary = []
for name, run in runs.items():
    s_all = sorted(run['s'], key=lambda s: s['t'])
    if not s_all:
        print('\n== %s: no GTWATERDIAG lines' % name)
        continue
    series = every(s_all)
    t0 = run['go']
    if name.startswith('dry'):
        x0 = series[0]['x']
        def at(dist):
            for s in s_all:
                if (s['x'] - x0) / 100.0 >= dist:
                    return s
            return None
        a15, a30 = at(15.0), at(30.0)
        print('\n== %s (%s): speed at 15 m %.2f m/s (t %.2f s), at 30 m %.2f m/s (t %.2f s)' % (
            name, run['why'], a15['v'] if a15 else -1, a15['t'] - t0 if a15 else -1, a30['v'] if a30 else -1, a30['t'] - t0 if a30 else -1))
        print('  the runner, per tick: %s' % dry_end.get(name, '-'))
        summary.append((name, run['why'], None))
        continue
    fname = name.split('_')[0]
    f = fords[fname]
    entry, exit_ = f['entry'], f['exit']
    startarc = run['startarc']
    def cross(arc, key='arc'):
        prev = None
        for s in s_all:
            if s[key] >= arc:
                if prev is None:
                    return s['t'] - t0, s['v']
                k = (arc - prev[key]) / max(1e-6, s[key] - prev[key])
                return prev['t'] - t0 + k * (s['t'] - prev['t']), prev['v'] + k * (s['v'] - prev['v'])
            prev = s
        return None, None
    te, ve = cross(entry)
    tx, vx = cross(exit_)
    tend, vend = cross(exit_ + 15.0)
    inw = [i for i, s in enumerate(series) if entry <= s['arc'] <= exit_]
    print('\n== %s (%s): start arc %.2f (15 m before the entry waterline %.2f); exit waterline %.2f' % (name, run['why'], startarc, entry, exit_))
    if te is not None:
        print('  entry: %.2f s, %.2f m/s' % (te, ve))
    if tx is not None:
        print('  exit:  %.2f s, %.2f m/s; waterline to waterline %.2f s (%.2f m, mean %.2f m/s)' % (tx, vx, tx - te, exit_ - entry, (exit_ - entry) / (tx - te)))
    if tend is not None:
        print('  15 m past the exit: %.2f s, %.2f m/s' % (tend, vend))
    if not inw:
        continue
    imin = min(inw, key=lambda i: series[i]['v'])
    smin = series[imin]
    print('  min in the water: %.2f m/s at arc %.2f (%+.2f m from the entry, %+.2f from the exit), t %.2f s, gear %d rpm %.0f engine %.0f Nm torque scale %.2f flooded %d' % (
        smin['v'], smin['arc'], smin['arc'] - entry, smin['arc'] - exit_, smin['t'] - t0, smin['gear'], smin['rpm'], smin['eng'], smin['tqs'], smin['flood']))
    print('  budget at the slowest point (N): ' + fmt_budget(budget(smin, accel(series, imin))))
    # equilibrium: >= 1 s within 0.1 m/s
    eq, i = [], inw[0]
    while i <= inw[-1]:
        j = i
        lo = hi = series[i]['v']
        while j + 1 <= inw[-1] and max(hi, series[j + 1]['v']) - min(lo, series[j + 1]['v']) < 0.1:
            j += 1
            lo, hi = min(lo, series[j]['v']), max(hi, series[j]['v'])
        if series[j]['t'] - series[i]['t'] >= 1.0:
            eq.append((series[i]['arc'] - entry, series[j]['arc'] - entry, series[j]['t'] - series[i]['t'], sum(series[k]['v'] for k in range(i, j + 1)) / (j - i + 1)))
            i = j + 1
        else:
            i += 1
    print('  equilibrium stretches (arc from the entry, duration, mean speed): %s' % ('; '.join('%.1f..%.1f m %.1f s %.2f m/s' % e for e in eq) if eq else 'none'))
    peak = max(((abs(w['sr']), w['sr'], k, s['arc']) for s in series if entry <= s['arc'] <= exit_ for k, w in enumerate(s['w']) if w['c'] == 1), default=(0, 0, -1, 0))
    print('  peak slip ratio in the water %.3f (w%d at arc %.2f); Chaos slipping in %d of %d wheel-samples' % (
        peak[1], peak[2], peak[3], sum(1 for s in series if entry <= s['arc'] <= exit_ for w in s['w'] if w['sl'] == 1), 4 * len(inw)))
    print('  through the water every ~2 m: arc-entry | v | a | tractive/cap | roll(water/mud) | hull | lift | spring+lift/weight | grade | unexplained | sink F/R cm | depth F m | pitch')
    last = -99
    for i in inw:
        s = series[i]
        if s['arc'] - last < 2.0 and i != imin:
            continue
        last = s['arc']
        b = budget(s, accel(series, i))
        w = s['w']
        print('   %5.1f | %.2f | %+.2f | %5.0f/%5.0f | %5.0f (%4.0f/%4.0f) | %4.0f | %5.0f | %5.0f/%5.0f | %+5.0f | %+5.0f | %2.0f %2.0f / %2.0f %2.0f | %.2f %.2f | %+.1f%s' % (
            s['arc'] - entry, s['v'], accel(series, i), b['trac'], b['cap'], b['roll'], b['water'], b['mud'], b['hull'], b['lift'],
            b['spring'] + b['lift'], b['weight'], b['grade'], b['resid'], w[0]['sink'] * 100, w[1]['sink'] * 100, w[2]['sink'] * 100, w[3]['sink'] * 100,
            w[0]['d'], w[1]['d'], s['pitch'], ' <- slowest' if i == imin else ''))
    # the whole water stretch, time-weighted means
    ws = [series[i] for i in inw]
    def mean(key):
        return sum(s[key] for s in ws) / len(ws)
    print('  means over the water: v %.2f | tractive %.0f | roll %.0f (water %.0f, uncapped %.0f) | hull drag %.0f | lift %.0f | springs %.0f' % (
        mean('v'), mean('tracN'), mean('rollN'), mean('waterN'), mean('waterRawN'), mean('hullAlongN'), mean('liftN'), mean('springN')))
    # exit bank, +-4 m of the exit waterline, 0.1 s
    win = [s for s in series if exit_ - 4.0 <= s['arc'] <= exit_ + 4.0]
    if win:
        best_step = (0, -1, 0)
        best_lstep = (0, -1, 0)
        best_load = (0, -1, 0)
        for a, b in zip(win, win[1:]):
            for k in range(4):
                wa, wb = a['w'][k], b['w'][k]
                if wa['c'] == 1 and wb['c'] == 1:
                    step = abs(wb['cz'] - wa['cz'])
                    if step > best_step[0]:
                        best_step = (step, k, wb['a'] - exit_)
                    ls = wb['L'] - wa['L']
                    if ls > best_lstep[0]:
                        best_lstep = (ls, k, wb['a'] - exit_)
                if wb['L'] > best_load[0]:
                    best_load = (wb['L'], k, wb['a'] - exit_)
        print('  exit bank +-4 m (0.1 s samples): biggest contact-Z step %.1f cm (w%d at %+.2f m from the waterline, its own arc); biggest load rise %+.0f N (w%d at %+.2f m); max load %.0f N (w%d at %+.2f m)' % (
            best_step[0], best_step[1], best_step[2], best_lstep[0], best_lstep[1], best_lstep[2], best_load[0], best_load[1], best_load[2]))
        # the per-tick lines at the bank: the biggest radius/sinkage change within 1 m of wheel travel, front wheels
        tick = [s for s in s_all if exit_ - 4.0 <= s['arc'] <= exit_ + 6.0]
        for k in (0, 1):
            worst = (0, 0, 0, 0, 0)
            for i, a in enumerate(tick):
                for b in tick[i + 1:]:
                    if b['w'][k]['a'] - a['w'][k]['a'] > 1.0:
                        break
                    d = abs(b['w'][k]['sink'] - a['w'][k]['sink'])
                    if d > worst[0]:
                        worst = (d, a['w'][k]['a'] - exit_, b['w'][k]['a'] - exit_, a['w'][k]['sink'], b['w'][k]['sink'])
            rs = [(abs(b['w'][k]['r'] - a['w'][k]['r']), b['w'][k]['a'] - exit_, a['w'][k]['r'], b['w'][k]['r'], a['w'][k]['tg'], b['w'][k]['tg'], b['t'] - a['t'])
                  for a, b in zip(tick, tick[1:])]
            r = max(rs, default=(0, 0, 0, 0, '', '', 0))
            print('  w%d: sinkage change within 1 m of travel: %.1f cm (from %.3f at %+.2f m to %.3f at %+.2f m); radius step between ticks %.1f cm (%.1f -> %.1f cm at %+.2f m, %s -> %s, %.3f s)' % (
                k, worst[0] * 100, worst[3], worst[1], worst[4], worst[2], r[0], r[2], r[3], r[1], r[4], r[5], r[6]))
        # around the radius jump, per tick: chassis z, pitch, front wheels
        if rows_dir:
            os.makedirs(rows_dir, exist_ok=True)
            with open(os.path.join(rows_dir, name + '_exit.txt'), 'w') as out:
                out.write('t arc-exit z pitch lift | per wheel: a-exit cz su sink r L tg\n')
                for s in win:
                    out.write('%.2f %+.2f %.1f %.2f %.0f | %s\n' % (s['t'] - t0, s['arc'] - exit_, s['z'], s['pitch'], s['liftN'], ' | '.join(
                        '%+.2f %.1f %.3f %.3f %.1f %.0f %s' % (w['a'] - exit_, w['cz'], w['su'], w['sink'], w['r'], w['L'], w['tg']) for w in s['w'])))
        jump = None
        for a, b in zip(tick, tick[1:]):
            if any(abs(b['w'][k]['r'] - a['w'][k]['r']) > 5.0 for k in range(4)):
                jump = b
                break
        if jump:
            j = tick.index(jump)
            print('  per tick around the first radius jump (t | arc-exit | chassis z | pitch | vz | w0 r/L/su | w1 r/L/su | w2 r/L | w3 r/L):')
            for s in tick[max(0, j - 2): j + 10]:
                w = s['w']
                print('   %.3f | %+.2f | %.1f | %.2f | %+.2f | %.1f/%.0f/%.2f | %.1f/%.0f/%.2f | %.1f/%.0f | %.1f/%.0f' % (
                    s['t'] - t0, s['arc'] - exit_, s['z'], s['pitch'], s['vz'], w[0]['r'], w[0]['L'], w[0]['su'], w[1]['r'], w[1]['L'], w[1]['su'],
                    w[2]['r'], w[2]['L'], w[3]['r'], w[3]['L']))
    # bow wave: front wheels in the last 2 m of water
    fr = [(w['d'], w['ds']) for s in s_all for w in s['w'][:2] if w['c'] == 1 and exit_ - 2.0 <= w['a'] <= exit_]
    if fr:
        print('  bow wave, front wheels in the last 2 m of water (%d wheel-ticks): read %.3f m mean vs still %.3f m mean; read - still: mean %+.3f, max %+.3f m' % (
            len(fr), sum(d for d, _ in fr) / len(fr), sum(ds for _, ds in fr) / len(fr), sum(d - ds for d, ds in fr) / len(fr), max(d - ds for d, ds in fr)))
    mid = [(w['d'], w['ds']) for s in s_all for w in s['w'][:2] if w['c'] == 1 and entry + 2.0 <= w['a'] <= exit_ - 2.0]
    if mid:
        print('  front wheels mid-crossing (entry+2 .. exit-2): read - still mean %+.3f m, max %+.3f m' % (sum(d - ds for d, ds in mid) / len(mid), max(d - ds for d, ds in mid)))
    summary.append((name, run['why'], (smin['v'], te, tx)))

print('\n== runs side by side: name | end | min speed in water | crossing time')
for name, why, v in summary:
    if v:
        vmin, te, tx = v
        print('  %-18s | %-22s | %.2f m/s | %s' % (name, why, vmin, '%.2f s' % (tx - te) if (tx is not None and te is not None) else 'did not cross'))

# terrain
for fname, rows in prof.items():
    f = fords[fname]
    rows.sort(key=lambda r: r['a'])
    level = f['level']
    print('\n== terrain %s: level %.1f cm; profile %.2f..%.2f every 25 cm' % (fname, level, rows[0]['a'], rows[-1]['a']))
    for side, wl, sign in (('entry', f['entry'], -1), ('exit', f['exit'], 1)):
        win = [r for r in rows if wl - 4.0 <= r['a'] <= wl + 4.0]
        for key in ('c', 'l', 'r'):
            for src, idx in (('trace', 1), ('heightfield', 0)):
                best = (-1e9, 0)
                best25 = (-1e9, 0)
                for i in range(len(win)):
                    if i + 2 < len(win):
                        rise = win[i + 2][key][idx] - win[i][key][idx]
                        if rise > best[0]:
                            best = (rise, win[i]['a'] - wl)
                    if i + 1 < len(win):
                        rise = win[i + 1][key][idx] - win[i][key][idx]
                        if rise > best25[0]:
                            best25 = (rise, win[i]['a'] - wl)
                if src == 'trace' or key == 'c':
                    print('  %s +-4 m, line %s (%s): biggest rise over 50 cm in the driving direction %.1f cm (from %+.2f m), over 25 cm %.1f cm (from %+.2f m)' % (
                        side, key, src, best[0], best[1], best25[0], best25[1]))
    c = [(r['a'], level - r['c'][0]) for r in rows]
    inside = [(a, d) for a, d in c if f['entry'] <= a <= f['exit']]
    dmax = max(d for _, d in inside)
    first95 = next(a for a, d in inside if d >= 0.95 * dmax)
    last95 = max(a for a, d in inside if d >= 0.95 * dmax)
    print('  bed (centre, heightfield): max depth %.1f cm; 95%% of it from %+.2f m after the entry to %+.2f m before the exit' % (dmax, first95 - f['entry'], f['exit'] - last95))
    for side, wl, sgn in (('entry', f['entry'], 1), ('exit', f['exit'], -1)):
        pts = []
        for dist in (0.5, 1, 2, 3, 4, 5, 6, 8, 10):
            a = wl + sgn * dist
            r = min(rows, key=lambda r: abs(r['a'] - a))
            pts.append('%g m %.1f' % (dist, level - r['c'][0]))
        print('  depth (cm) going in from the %s waterline: %s' % (side, ', '.join(pts)))
        # grade over each metre from the waterline inwards
        grades = []
        for dist in range(0, 6):
            a0, a1 = wl + sgn * dist, wl + sgn * (dist + 1)
            r0 = min(rows, key=lambda r: abs(r['a'] - a0))
            r1 = min(rows, key=lambda r: abs(r['a'] - a1))
            grades.append('%.0f%%' % ((r0['c'][0] - r1['c'][0]) / 1.0))
        outside = []
        for dist in range(1, 6):
            a0, a1 = wl - sgn * (dist - 1), wl - sgn * dist
            r0 = min(rows, key=lambda r: abs(r['a'] - a0))
            r1 = min(rows, key=lambda r: abs(r['a'] - a1))
            outside.append('%.0f%%' % ((r1['c'][0] - r0['c'][0]) / 1.0))
        print('  bank grade per metre (centre, rising away from the water): inside %s | outside %s' % (', '.join(grades), ', '.join(outside)))
    diffs = [(abs(r[k][1] - r[k][0]), r['a'], k) for r in rows for k in ('c', 'l', 'r') if r[k][4] == 'L']
    an = [(abs(r['c'][2] - r['c'][0]), r['a']) for r in rows]
    print('  trace vs heightfield on the landscape: max |diff| %.1f cm (arc %.2f, line %s); analytic vs heightfield (centre) max %.1f cm (arc %.2f)' % (
        max(diffs)[0], max(diffs)[1], max(diffs)[2], max(an)[0], max(an)[1]))
    hits = sorted(set(r[k][4] for r in rows for k in ('c', 'l', 'r')))
    print('  what the traces hit on the three lines: %s' % ', '.join(hits))

if rocks:
    print('\n== rocks (%d): offsets from the route (negative = right of the driving direction)' % len(rocks))
    for r in rocks:
        edge = abs(r['off']) - r['size'] * 0.5
        print('  rock %2d %s arc %.2f off %+.2f size %.2f top %.1f cm: from exit %+.2f m, from entry %+.2f m, near edge %.2f m from the centre line' % (
            r['i'], r['ford'], r['arc'], r['off'], r['size'], r['top'], r['rel_exit'], r['rel_entry'], edge))
    print('  closest near edge to the centre line: %.2f m' % min(abs(r['off']) - r['size'] * 0.5 for r in rocks))
