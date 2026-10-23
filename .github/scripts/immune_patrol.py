"""Fig. 03 — Immune Patrol.

Turns the public contribution calendar into tissue, seeds a daily outbreak of
antigens that spread to neighbouring days, and simulates a phagocyte that hunts
them down (greedy, nearest first). The result is a self-contained animated SVG
(SMIL only, no scripts, no external references).

Usage: python immune_patrol.py <github-user> <output.svg>
Standard library only, so the workflow needs no dependencies.
"""
import random
import re
import sys
import urllib.request
from datetime import date

USER, OUT = sys.argv[1], sys.argv[2]

# ── tokens (match docs/UI/github-profile-design.md) ─────────────────────────
TEAL, CYAN, VIOLET, CORAL = "#34D1BF", "#5AB8FF", "#A391FF", "#FF8E6E"
MIST, BONE, DIM = "#8B9BB4", "#E6ECF5", "#5D6E8A"
SERIF = "Georgia, 'Iowan Old Style', 'Times New Roman', serif"
SANS = "'Segoe UI', -apple-system, 'Helvetica Neue', Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"

# ── simulation constants ────────────────────────────────────────────────────
STEP = 0.11        # seconds per grid move
ENGULF = 0.45      # seconds spent engulfing
SPREAD = 3.6       # an untreated antigen infects a neighbour this often
SEEDS = 7          # initial antigens
CAP = 22           # maximum antigens per outbreak
OUTRO = 3.5        # "all clear" hold before the loop restarts

# ── layout ──────────────────────────────────────────────────────────────────
W, H = 1000, 330
PITCH, CELL = 15, 12


def fetch_calendar(user):
    req = urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                 headers={"User-Agent": "immune-patrol"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    days = {}
    for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        d = re.search(r'data-date="([\d-]+)"', td)
        lv = re.search(r'data-level="(\d)"', td)
        pos = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', td)
        if d and lv and pos:
            days[(int(pos.group(2)), int(pos.group(1)))] = (d.group(1), int(lv.group(1)))
    if not days:
        raise SystemExit("no contribution data found")
    return days


def simulate(cells, rng):
    """Returns antigens [(cell, t_appear, t_cleared)], phagocyte route [(t, cell)], end time."""
    free = [c for c in cells]
    rng.shuffle(free)
    antigens = []                       # dicts: cell, born, cleared, next_spread
    for i, c in enumerate(free[:SEEDS]):
        born = 0.6 + i * 0.35
        antigens.append({"cell": c, "born": born, "cleared": None, "next": born + SPREAD})
    occupied = {a["cell"] for a in antigens}
    pos = (0, 3)
    t = 0.0
    route = [(t, pos)]

    def spread_until(now):
        changed = True
        while changed:
            changed = False
            for a in list(antigens):
                if a["cleared"] is None and a["next"] <= now and len(antigens) < CAP:
                    x, y = a["cell"]
                    options = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                               if (x + dx, y + dy) in cells and (x + dx, y + dy) not in occupied]
                    if options:
                        n = rng.choice(options)
                        occupied.add(n)
                        antigens.append({"cell": n, "born": a["next"], "cleared": None,
                                         "next": a["next"] + SPREAD})
                    a["next"] += SPREAD
                    changed = True

    while True:
        spread_until(t)
        alive = [a for a in antigens if a["cleared"] is None and a["born"] <= t]
        if not alive:
            pending = [a for a in antigens if a["cleared"] is None]
            if not pending:
                break
            t = min(a["born"] for a in pending)  # wait for the next one to appear
            route.append((t, pos))
            continue
        target = min(alive, key=lambda a: (abs(a["cell"][0] - pos[0]) + abs(a["cell"][1] - pos[1]),
                                           a["born"]))
        tx, ty = target["cell"]
        while pos != (tx, ty):              # walk: rows first, then columns
            x, y = pos
            pos = (x, y + (1 if ty > y else -1)) if y != ty else (x + (1 if tx > x else -1), y)
            t += STEP
            route.append((t, pos))
            spread_until(t)
        t += ENGULF
        target["cleared"] = t
        route.append((t, pos))
    return antigens, route, t + OUTRO


def main():
    days = fetch_calendar(USER)
    last = max(d for d, _ in days.values())
    rng = random.Random(f"{USER}:{last}")   # a new outbreak every day
    cells = set(days)
    antigens, route, T = simulate(cells, rng)
    cols = max(c[0] for c in cells) + 1
    gx = (W - cols * PITCH + (PITCH - CELL)) / 2
    gy = 114

    def cx(c):
        return gx + c[0] * PITCH + CELL / 2

    def cy(c):
        return gy + c[1] * PITCH + CELL / 2

    def kt(*ts):
        """Fractions of the loop, forced non-decreasing so SMIL accepts them."""
        out, prev = [], 0.0
        for x in ts:
            prev = max(prev, min(max(x / T, 0), 1))
            out.append(f"{prev:.4f}")
        return ";".join(out)

    o = []
    w = o.append
    total = len(antigens)
    w(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    w('<title id="t">Fig. 03 — Immune Patrol</title>')
    w(f'<desc id="d">Each square is one day of {USER}\'s GitHub contributions, drawn as tissue. '
      f'{SEEDS} antigens appear and spread to neighbouring days; a phagocyte hunts them down and contains all {total}. '
      f'A new outbreak is generated every day.</desc>')
    w(f'<!-- Generated by .github/scripts/immune_patrol.py for {last}. Do not edit by hand. -->')
    w(f'''<defs>
  <radialGradient id="bg" cx="0.5" cy="0.4" r="0.8">
    <stop offset="0" stop-color="#0E1A30"/><stop offset="0.6" stop-color="#091120"/><stop offset="1" stop-color="#060A13"/>
  </radialGradient>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="11" cy="11" r="0.8" fill="#1C2942"/></pattern>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="1.8" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="plate"><rect width="{W}" height="{H}" rx="22"/></clipPath>
  <g id="ag"><circle r="2.6" fill="{CORAL}"/><path d="M3.4 0 H5 M-3.4 0 H-5 M0 3.4 V5 M0 -3.4 V-5" stroke="{CORAL}" stroke-width="1.1" stroke-linecap="round"/></g>
</defs>''')
    w(f'<g clip-path="url(#plate)"><rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#dots)" opacity="0.7"/></g>')
    w(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="22" fill="none" stroke="#1C2942"/>')
    w(f'<path d="M20 36 V20 H36 M964 20 H980 V36 M980 {H - 36} V{H - 20} H964 M36 {H - 20} H20 V{H - 36}" fill="none" stroke="#2A3A5A"/>')

    # header
    w(f'<rect x="56" y="47" width="7" height="7" fill="{VIOLET}"/>')
    w(f'<text x="72" y="55" font-family="{MONO}" font-size="11.5" letter-spacing="3" fill="{MIST}">FIG. 03 — IMMUNE PATROL</text>')
    w(f'<text x="944" y="55" font-family="{SERIF}" font-size="14" font-style="italic" fill="{MIST}" text-anchor="end">tissue: the last year of my contributions</text>')

    # month labels
    seen = set()
    for (col, row), (d, _) in sorted(days.items()):
        if row == 0 and d[8:10] <= "07" and d[:7] not in seen:
            seen.add(d[:7])
            m = date.fromisoformat(d).strftime("%b").upper()
            w(f'<text x="{gx + col * PITCH:.1f}" y="{gy - 10}" font-family="{MONO}" font-size="9.5" letter-spacing="1" fill="{DIM}">{m}</text>')

    # tissue
    w('<!-- tissue: one square per day; contribution level = tissue density -->')
    alpha = {0: None, 1: 0.35, 2: 0.55, 3: 0.78, 4: 1}
    for (col, row), (d, lv) in sorted(days.items()):
        x, y = gx + col * PITCH, gy + row * PITCH
        fill = f'fill="{TEAL}" fill-opacity="{alpha[lv]}"' if lv else 'fill="#13203A"'
        w(f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" {fill}/>')

    # infection, antigens and memory marks
    w('<!-- each antigen: inflamed cell, the antigen itself, then a memory mark once contained -->')
    for a in antigens:
        c, b, k = a["cell"], a["born"], a["cleared"]
        x, y = gx + c[0] * PITCH, gy + c[1] * PITCH
        w(f'<rect x="{x:.1f}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{CORAL}" opacity="0">'
          f'<animate attributeName="opacity" values="0;0;0.28;0.28;0;0" keyTimes="0;{kt(b, b + 0.25, k, k + 0.3)};1" dur="{T:.2f}s" repeatCount="indefinite"/></rect>')
        w(f'<use href="#ag" x="{cx(c):.1f}" y="{cy(c):.1f}" opacity="0">'
          f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{kt(b, b + 0.25, k - ENGULF, k)};1" dur="{T:.2f}s" repeatCount="indefinite"/></use>')
        w(f'<circle cx="{cx(c):.1f}" cy="{cy(c):.1f}" r="3.3" fill="none" stroke="{VIOLET}" stroke-width="1.2" opacity="0">'
          f'<animate attributeName="opacity" values="0;0;0.9;0.9;0" keyTimes="0;{kt(k, k + 0.3, T - 0.6)};1" dur="{T:.2f}s" repeatCount="indefinite"/></circle>')

    # phagocyte: motion along the route, with pauses encoded as keyPoints
    steps = []
    n = 0
    for i, (t, c) in enumerate(route):
        if i and c != route[i - 1][1]:
            n += 1
        steps.append((t, n))
    total_steps = max(n, 1)
    pts = [route[0][1]] + [c for i, (_, c) in enumerate(route) if i and c != route[i - 1][1]]
    path = "M" + " L".join(f"{cx(c):.1f} {cy(c):.1f}" for c in pts)
    # keep only the points where speed changes, then close the loop at T
    keys = [steps[0]]
    for i in range(1, len(steps) - 1):
        (t0, n0), (t1, n1), (t2, n2) = steps[i - 1], steps[i], steps[i + 1]
        if (n1 - n0 > 0) != (n2 - n1 > 0):
            keys.append(steps[i])
    keys.append(steps[-1])
    keys.append((T, steps[-1][1]))
    key_times = ";".join(f"{min(t / T, 1):.4f}" for t, _ in keys)
    key_points = ";".join(f"{k / total_steps:.4f}" for _, k in keys)
    end = route[-1][0]
    w('<!-- the phagocyte -->')
    w(f'<g filter="url(#glow)">')
    w(f'  <animateMotion path="{path}" keyPoints="{key_points}" keyTimes="{key_times}" calcMode="linear" dur="{T:.2f}s" repeatCount="indefinite"/>')
    w(f'  <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;{kt(0.4, T - 0.5)};1" dur="{T:.2f}s" repeatCount="indefinite"/>')
    w(f'  <circle r="6.2" fill="#0B1424" stroke="{VIOLET}" stroke-width="1.6"/>')
    w(f'  <circle r="2" fill="{VIOLET}"/>')
    w(f'  <path d="M6.2 0 H8.6 M8.6 0 L10.4 -1.8 M8.6 0 L10.4 1.8" stroke="{VIOLET}" stroke-width="1.1" stroke-linecap="round" fill="none">'
      f'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="2.4s" repeatCount="indefinite"/></path>')
    w('</g>')

    # HUD: containment counter and tissue status
    hy = gy + 7 * PITCH + 34
    w(f'<text x="{gx:.1f}" y="{hy}" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{MIST}">CONTAINED</text>')
    clears = sorted(a["cleared"] for a in antigens)
    marks = [0.0] + clears + [T]
    for i in range(len(marks) - 1):
        s, e = marks[i], marks[i + 1]
        if i == 0:
            vals, times = "1;0", f"0;{kt(e)}"
        elif e >= T:
            vals, times = "0;1", f"0;{kt(s)}"
        else:
            vals, times = "0;1;0", f"0;{kt(s, e)}"
        w(f'<text x="{gx + 112:.1f}" y="{hy}" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{BONE}" opacity="{1 if i == 0 else 0}">'
          f'{i:02d} / {total:02d}<animate attributeName="opacity" values="{vals}" keyTimes="{times}" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></text>')
    rx = gx + cols * PITCH - (PITCH - CELL)
    w(f'<text x="{rx - 92:.1f}" y="{hy}" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{MIST}" text-anchor="end">TISSUE</text>')
    w(f'<text x="{rx:.1f}" y="{hy}" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{CORAL}" text-anchor="end">INFLAMED'
      f'<animate attributeName="opacity" values="1;0;0" keyTimes="0;{kt(end)};1" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></text>')
    w(f'<text x="{rx:.1f}" y="{hy}" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{TEAL}" text-anchor="end" opacity="0">ALL CLEAR'
      f'<animate attributeName="opacity" values="0;1;1" keyTimes="0;{kt(end)};1" calcMode="discrete" dur="{T:.2f}s" repeatCount="indefinite"/></text>')

    # legend + caption
    ly = H - 52
    w(f'<g font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{MIST}">')
    w(f'  <rect x="{gx:.1f}" y="{ly - 8}" width="9" height="9" rx="2" fill="{TEAL}"/><text x="{gx + 15:.1f}" y="{ly}">ACTIVITY</text>')
    w(f'  <use href="#ag" x="{gx + 112:.1f}" y="{ly - 3.5}"/><text x="{gx + 122:.1f}" y="{ly}">ANTIGEN</text>')
    w(f'  <circle cx="{gx + 214:.1f}" cy="{ly - 3.5}" r="4.6" fill="#0B1424" stroke="{VIOLET}" stroke-width="1.4"/><text x="{gx + 226:.1f}" y="{ly}">PHAGOCYTE</text>')
    w(f'  <circle cx="{gx + 336:.1f}" cy="{ly - 3.5}" r="3.3" fill="none" stroke="{VIOLET}" stroke-width="1.2"/><text x="{gx + 346:.1f}" y="{ly}">MEMORY</text>')
    w('</g>')
    w(f'<text x="{rx:.1f}" y="{ly}" font-family="{SERIF}" font-size="13" font-style="italic" fill="{DIM}" text-anchor="end">a new outbreak every day · {last}</text>')
    w('</svg>')

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(o) + "\n")
    print(f"{OUT}: {total} antigens, {len(route)} moves, loop {T:.1f}s")


main()
