"""Builds assets/stats.svg (neon contribution stats) from public GitHub data.
Runs daily via .github/workflows/stats.yml. Standard library only."""
import re, os, sys, json, random, datetime as dt, urllib.request

USER = os.environ.get("GH_USER", "4mh24cs167-tech")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "stats.svg")
GLY = json.load(open(os.path.join(HERE, "glyphs.json")))
BG0, MAG, VIO, CY, TXT, MUT = "#05020c", "#ff2bd6", "#9b4dff", "#22e4ff", "#f3eaff", "#a99bc9"
LEVELS = ["#170a30", "#3d1470", "#7b22c9", "#c92fe8", "#ff2bd6"]

# ---------- text as vector paths ----------
class Doc:
    def __init__(self): self.used = {}
    def width(self, t, font, size, ls=0):
        f = GLY[font]; sc = size / f["upm"]
        return sum(f["g"].get(c, f["g"][" "])[0] * sc + ls for c in t) - (ls if t else 0)
    def text(self, t, font, size, x, y, fill, anchor="start", ls=0):
        f = GLY[font]; sc = size / f["upm"]; w = self.width(t, font, size, ls)
        x -= w / 2 if anchor == "middle" else (w if anchor == "end" else 0)
        out = []
        for c in t:
            adv, d = f["g"].get(c, f["g"][" "])
            if c != " " and d:
                gid = f"{font}{ord(c)}"; self.used[gid] = d
                out.append(f'<use href="#{gid}" transform="translate({x:.1f} {y:.1f}) scale({sc:.5f} {-sc:.5f})"/>')
            x += adv * sc + ls
        return f'<g fill="{fill}">{"".join(out)}</g>'
    def defs(self): return "".join(f'<path id="{k}" d="{v}"/>' for k, v in self.used.items())

# ---------- data ----------
def fetch():
    req = urllib.request.Request(f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "profile-stats"})
    page = urllib.request.urlopen(req, timeout=30).read().decode()
    tips = {}
    for tid, txt in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        m = re.match(r"\s*(\d[\d,]*) contribution", txt); tips[tid] = int(m.group(1).replace(",", "")) if m else 0
    days = []
    for a in re.findall(r"<td([^>]*ContributionCalendar-day[^>]*)>", page):
        d = re.search(r'data-date="([^"]+)"', a); i = re.search(r'id="([^"]+)"', a); lv = re.search(r'data-level="(\d)"', a)
        if d and i: days.append((dt.date.fromisoformat(d.group(1)), tips.get(i.group(1), 0), int(lv.group(1)) if lv else 0))
    if not days: sys.exit("no calendar data")
    return sorted(days)

def summarize(days):
    total = sum(c for _, c, _ in days); active = sum(1 for _, c, _ in days if c)
    best = max(days, key=lambda x: x[1])
    longest = run = 0; ls = le = rs = None
    for d, c, _ in days:
        if c:
            run += 1; rs = rs or d
            if run > longest: longest, ls, le = run, rs, d
        else: run, rs = 0, None
    cur = 0; i = len(days) - 1; cs = ce = None
    if days[i][1] == 0: i -= 1
    while i >= 0 and days[i][1]: cur += 1; cs = days[i][0]; ce = ce or days[i][0]; i -= 1
    return dict(total=total, active=active, best=best, longest=longest, ls=ls, le=le, cur=cur, cs=cs, ce=ce)

def f(d): return f"{d.strftime('%b').upper()} {d.day}" if d else "-"

def cut(x, y, w, h, c): return f"M{x+c} {y}H{x+w}V{y+h-c}L{x+w-c} {y+h}H{x}V{y+c}Z"

# ---------- render ----------
def render(days, s):
    W, H = 1000, 430; d = Doc()
    tiles = [("CONTRIBUTIONS", f'{s["total"]:,}', "LAST 12 MONTHS", TXT),
             ("CURRENT STREAK", str(s["cur"]), f'{f(s["cs"])} - {f(s["ce"])}' if s["cur"] else "RESTARTING", MAG),
             ("LONGEST STREAK", str(s["longest"]), f'{f(s["ls"])} - {f(s["le"])}' if s["longest"] else "-", TXT),
             ("BEST DAY", str(s["best"][1]), f(s["best"][0]) if s["best"][1] else "-", CY),
             ("ACTIVE DAYS", str(s["active"]), "OUT OF 365", TXT)]
    body = ""; tw = (W - 60 - 4 * 12) / 5
    for i, (lab, val, sub, col) in enumerate(tiles):
        x = 30 + i * (tw + 12); y = 30
        body += f'<path d="{cut(x, y, tw, 122, 12)}" fill="#12052c" stroke="{col}" stroke-opacity=".55"/>'
        body += d.text(lab, "orbb", 10, x + tw / 2, y + 28, MUT, "middle", 1.6)
        body += f'<g class="{"glow" if col == MAG else ""}" filter="url(#glow)">' + d.text(val, "orb", 38, x + tw / 2, y + 78, col, "middle", 1) + "</g>"
        body += d.text(sub, "mono", 11, x + tw / 2, y + 104, MUT, "middle", .6)
    # heatmap
    first = days[0][0]; start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    cell, gap = 13, 3.4; ncols = (days[-1][0] - start).days // 7 + 1
    gw = ncols * (cell + gap); ox = (W - gw) / 2 + 14; oy = 210
    cells = ""; months = ""
    for day, c, lv in days:
        col = (day - start).days // 7; row = (day.weekday() + 1) % 7
        x = ox + col * (cell + gap); y = oy + row * (cell + gap)
        cls = f' class="c" style="animation-delay:{col*.03:.2f}s"' if lv else ""
        cells += f'<rect{cls} x="{x:.1f}" y="{y:.1f}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[lv]}"/>'
        if day.day <= 7 and row == 0 and col < ncols - 2:
            months += d.text(day.strftime("%b").upper(), "mono", 10.5, x, oy - 9, MUT, ls=.5)
    for r, t in [(1, "MON"), (3, "WED"), (5, "FRI")]:
        body += d.text(t, "mono", 10, ox - 10, oy + r * (cell + gap) + 10, MUT, "end")
    gh = 7 * (cell + gap)
    legend = "".join(f'<rect x="{W-60-5*17+i*17}" y="{H-40}" width="12" height="12" rx="2" fill="{c}"/>' for i, c in enumerate(LEVELS))
    sync = d.text(f"LAST SYNC  {dt.date.today().isoformat()}  //  AUTO-UPDATED DAILY", "mono", 11, 30, H - 30, MUT, ls=1)
    less = d.text("LESS", "mono", 10, W - 68 - 5 * 17, H - 30, MUT, "end") + d.text("MORE", "mono", 10, W - 54, H - 30, MUT)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>{d.defs()}
<linearGradient id="ng" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{MAG}"/><stop offset=".55" stop-color="{VIO}"/><stop offset="1" stop-color="{CY}"/></linearGradient>
<linearGradient id="pbg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#140630"/><stop offset="1" stop-color="{BG0}"/></linearGradient>
<linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="{CY}" stop-opacity="0"/><stop offset=".5" stop-color="{CY}" stop-opacity=".22"/><stop offset="1" stop-color="{CY}" stop-opacity="0"/></linearGradient>
<filter id="glow" x="-30%" y="-50%" width="160%" height="200%"><feGaussianBlur stdDeviation="3.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="{VIO}" stroke-opacity=".08"/></pattern>
<clipPath id="cl"><path d="{cut(1, 1, W-2, H-2, 24)}"/></clipPath><clipPath id="hm"><rect x="{ox}" y="{oy}" width="{gw}" height="{gh}"/></clipPath></defs>
<style>.c{{animation:c .5s ease-out both}}@keyframes c{{from{{opacity:0}}}}
.glow{{animation:gl 2.4s ease-in-out infinite}}@keyframes gl{{50%{{opacity:.6}}}}
.sc{{animation:sc 5s linear infinite}}@keyframes sc{{0%{{transform:translateX(-140px)}}70%,100%{{transform:translateX({gw+140:.0f}px)}}}}</style>
<g clip-path="url(#cl)"><rect width="{W}" height="{H}" fill="url(#pbg)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>
{body}{months}{cells}
<g clip-path="url(#hm)"><rect class="sc" x="{ox}" y="{oy}" width="140" height="{gh}" fill="url(#scan)"/></g>
{sync}{less}{legend}</g>
<path d="{cut(1, 1, W-2, H-2, 24)}" fill="none" stroke="url(#ng)" stroke-width="2" filter="url(#glow)"/></svg>'''

if __name__ == "__main__":
    days = fetch(); s = summarize(days)
    open(OUT, "w").write(render(days, s))
    print("stats.svg written:", s["total"], "contributions, streak", s["cur"])
