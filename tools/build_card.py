#!/usr/bin/env python3
"""Build the profile card SVGs from an ASCII portrait and a few facts.

    python3 tools/build_card.py                     # chosen variant -> assets/
    python3 tools/build_card.py --all --out DIR     # every variant, for review
    python3 tools/build_card.py --refresh-portrait  # re-fetch the avatar, redo the ASCII

Writes assets/card-dark.svg (desktop) and assets/card-dark-narrow.svg (phones); the README
shows the dark card in both GitHub themes. --all also renders the light theme.
Needs the Python 3 standard library, plus ImageMagick (`magick`) when the portrait is rebuilt.
"""
import argparse
import subprocess
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
AVATAR = "https://avatars.githubusercontent.com/u/257558873?s=460"
CHOSEN = "portrait"

MONO = "ui-monospace, 'DejaVu Sans Mono', 'Cascadia Mono', SFMono-Regular, Menlo, Consolas, monospace"
CHAR_W = 0.6  # monospace advance as a fraction of font size
LINE = 1.2    # portrait line height as a fraction of font size

# Facts only. Edit here, then rebuild.
NAME, USER, HOST = "Hrushikesh M", "hrushikesh", "mysore"
TAGLINE = "Learning by building. Exploring as I go."
FACTS = [
    ("Exploring", "Agentic AI, then security for AI agents"),
    ("Study", "BCA, 2nd year, NIE FGC Mysore"),
    ("Placed", "2nd, Prayag national product development"),
    ("", "3rd, Cyber-clash state-level hackathon"),
    None,
    ("Languages", "Python, JavaScript, Bash, C++ (Arduino)"),
    ("Rig", "ThinkPad T430, CachyOS Linux"),
    ("Uptime", "19 years"),
    None,
    ("Open to", "Internships and freelance work"),
    ("LinkedIn", "in/hrushikesh-m-b063a23b7"),
]

THEMES = {
    "dark": dict(bg="#0E3B39", panel="#0A2F2D", ink="#E6EEE9", muted="#9DB8B1", gold="#E0B04A", rule="#2C5C58",
                 swatches=["#1F6B60", "#3F8F7A", "#9DB8B1", "#E0B04A", "#C98A2E", "#B8323F"]),
    "light": dict(bg="#E9F0EC", panel="#F4F8F5", ink="#12302E", muted="#4C6964", gold="#7A5510", rule="#B9CCC5",
                  swatches=["#12302E", "#1F6B60", "#3F8F7A", "#7A5510", "#A8741C", "#9E2A36"]),
}

RAMP = " .,:;i1tfLCG08@"  # little ink -> lots of ink


# ---------- portrait ----------
def make_portrait(cols, bright, out):
    """Avatar -> ASCII. bright=False: more ink where the photo is dark (for light cards).
    bright=True: more ink where the photo is light (for dark cards, so it isn't a negative)."""
    cw, ch = 300, 318  # crop (px) around head and shoulders of the 413 px avatar
    rows = round(cols * CHAR_W / LINE * ch / cw)
    raw = urllib.request.urlopen(AVATAR, timeout=20).read()
    pgm = subprocess.run(
        ["magick", "-", "-resize", "413x413!", "-crop", f"{cw}x{ch}+56+22", "+repage", "-colorspace", "gray",
         "-resize", f"{cols}x{rows}!", "-level", "6%,94%", "-sigmoidal-contrast", "5x58%", "-depth", "8", "pgm:-"],
        input=raw, capture_output=True, check=True).stdout
    _, size, _, px = pgm.split(b"\n", 3)
    w, h = map(int, size.split())
    # background = bright pixels connected to the border (flood fill)
    bg, stack = set(), [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if (x, y) in bg or not (0 <= x < w and 0 <= y < h) or px[y * w + x] < 226:
            continue
        bg.add((x, y))
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    n = len(RAMP)
    lines = []
    for y in range(h):
        row = ""
        for x in range(w):
            v = px[y * w + x]
            ink = v if bright else 255 - v
            row += " " if (x, y) in bg else RAMP[max(1, min(n - 1, int(ink / 256 * n)))]
        lines.append(row.rstrip())
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    out.write_text("\n".join(lines) + "\n")


def portrait(cols, bright):
    f = TOOLS / f"portrait-{cols}{'-bright' if bright else ''}.txt"
    if not f.exists():
        make_portrait(cols, bright, f)
    return f.read_text().rstrip("\n").split("\n")


# ---------- svg helpers ----------
def text(x, y, s, size, fill, weight=400, opacity=None, anchor=None, stretch="spacing"):
    """One line. textLength pins the width so any monospace fallback lines up;
    only the ASCII art may stretch glyphs, everything else adjusts spacing only."""
    if not s:
        return ""
    a = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"'
    if weight != 400:
        a += f' font-weight="{weight}"'
    if opacity is not None:
        a += f' fill-opacity="{opacity}"'
    if anchor:
        a += f' text-anchor="{anchor}"'
    else:
        a += f' textLength="{len(s) * size * CHAR_W:.1f}" lengthAdjust="{stretch}"'
    return f'<text {a} xml:space="preserve">{escape(s)}</text>'


def art(x, y, lines, size, t, weight=700, graded=False):
    """ASCII portrait. graded: glyph density also sets opacity (gold-leaf look)."""
    out, cw = [], size * CHAR_W
    levels = (0.78, 0.86, 0.94, 1.0)
    op = {c: levels[min(3, i * 4 // len(RAMP))] for i, c in enumerate(RAMP)}
    for i, line in enumerate(lines):
        ly = y + i * size * LINE
        if not graded:
            out.append(text(x, ly, line, size, t["gold"], weight, stretch="spacingAndGlyphs"))
            continue
        run, start, cur = "", 0, None
        for j, ch in enumerate(line + "\0"):
            o = None if ch in " \0" else op[ch]
            if o != cur:
                if run.strip():
                    out.append(text(x + start * cw, ly, run, size, t["gold"], weight,
                                    opacity=cur if cur < 1 else None, stretch="spacingAndGlyphs"))
                run, start, cur = "", j, o
            if ch != "\0":
                run += ch
    return "".join(out), len(lines) * size * LINE


def facts(x, y, size, t, lh=1.6, name_row=False):
    rows = ([("Name", NAME)] if name_row else []) + FACTS
    keyw = max(len(k) for k, _ in filter(None, rows)) + 2
    cw, out = size * CHAR_W, []
    for f in rows:
        if f:
            k, v = f
            if k:
                out.append(text(x, y, f"{k}:", size, t["gold"], 600))
            out.append(text(x + keyw * cw, y, v, size, t["ink"]))
        y += size * lh * (1 if f else 0.55)
    y += size * 0.3
    out.append("".join(f'<rect x="{x + i * size * 1.8:.1f}" y="{y:.1f}" width="{size * 1.8:.1f}" height="{size:.1f}" fill="{c}"/>'
                       for i, c in enumerate(t["swatches"])))
    return "".join(out), y + size


def header(x, y, size, t):
    """user@host, then a rule the same length (neofetch header)."""
    cw = size * CHAR_W
    return (text(x, y, USER, size, t["gold"], 700) + text(x + len(USER) * cw, y, f"@{HOST}", size, t["ink"], 700)
            + text(x, y + size * 1.5, "-" * len(USER + HOST + "@"), size, t["muted"])), y + size * 3.1


def svg(w, h, slug, t, body, style=""):
    desc = (f"ASCII portrait of {NAME} drawn from his photo, beside his facts: exploring agentic AI, then security "
            "for AI agents; BCA 2nd year at NIE FGC Mysore; 2nd place at Prayag, a national product development "
            "competition; 3rd at Cyber-clash, a state-level hackathon; works in Python, JavaScript, Bash and C++; "
            "ThinkPad T430 with CachyOS; 19 years old; open to internships and freelance work.")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h:.0f}" width="{w}" height="{h:.0f}" '
            f'role="img" aria-labelledby="{slug}-t {slug}-d" font-family="{MONO}">'
            f'<title id="{slug}-t">{escape(NAME)}: profile card</title><desc id="{slug}-d">{escape(desc)}</desc>'
            f'{f"<style>{style}</style>" if style else ""}'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1:.0f}" rx="12" fill="{t["bg"]}" stroke="{t["rule"]}"/>{body}</svg>\n')


# ---------- variants ----------
def neofetch(theme, narrow):
    t, slug = THEMES[theme], f"neofetch-{theme}{'-n' if narrow else ''}"
    p = portrait(60, theme == "dark")
    if narrow:
        W, ps, fs = 560, 7.5, 17
        a, ah = art((W - 60 * ps * CHAR_W) / 2, 40, p, ps, t)
        hd, y = header(32, 40 + ah + 40, fs, t)
        f, fh = facts(32, y, fs, t, name_row=True)
    else:
        W, ps, fs = 1000, 10.5, 16
        a, ah = art(40, 52, p, ps, t)
        hd, y = header(470, 70, fs, t)
        f, fh = facts(470, y, fs, t, name_row=True)
    return svg(W, max(52 + ah, fh) + 34, slug, t, a + hd + f)


def terminal(theme, narrow):
    t, slug = THEMES[theme], f"terminal-{theme}{'-n' if narrow else ''}"
    p = portrait(52, theme == "dark")
    W = 560 if narrow else 1000
    ps, fs = (7.2, 16) if narrow else (9.5, 15)
    wx, wy, ww, bar = 16, 16, W - 32, 34
    prompt = f"[{USER}@{HOST} ~]$ "
    cw = fs * CHAR_W
    cy = wy + bar + 34
    px0 = wx + 22
    top = [text(wx + ww / 2, wy + 22, f"{USER}@{HOST}: ~", 13, t["muted"], anchor="middle"),
           f'<g stroke="{t["muted"]}" stroke-width="1.4" fill="none" stroke-linecap="round">'
           f'<path d="M{wx + ww - 82} {wy + 17}h9"/><path d="M{wx + ww - 52} {wy + 12}l5 5l5 -5"/>'
           f'<path d="M{wx + ww - 24} {wy + 12}l9 9M{wx + ww - 15} {wy + 12}l-9 9"/></g>',
           text(px0, cy, prompt, fs, t["muted"]),
           f'<clipPath id="{slug}-typed"><rect class="typer" x="{px0 + len(prompt) * cw:.1f}" y="{cy - fs:.1f}" '
           f'width="{9 * cw:.1f}" height="{fs * 1.4:.1f}"/></clipPath>',
           f'<g clip-path="url(#{slug}-typed)">{text(px0 + len(prompt) * cw, cy, "fastfetch", fs, t["ink"], 600)}</g>']
    oy = cy + 32
    if narrow:
        a, ah = art((W - 52 * ps * CHAR_W) / 2, oy, p, ps, t)
        hd, y = header(px0, oy + ah + 34, fs, t)
        f, fh = facts(px0, y, fs, t, name_row=True)
    else:
        a, ah = art(px0, oy, p, ps, t)
        ix = px0 + 52 * ps * CHAR_W + 44
        hd, y = header(ix, oy + 10, fs, t)
        f, fh = facts(ix, y, fs, t, name_row=True)
    end = max(oy + ah, fh) + 34
    tail = text(px0, end, prompt, fs, t["muted"]) + (
        f'<rect class="cursor" x="{px0 + len(prompt) * cw:.1f}" y="{end - fs * 0.85:.1f}" width="{cw:.1f}" '
        f'height="{fs * 1.05:.1f}" fill="{t["gold"]}"/>')
    wh = end + 24 - wy
    frame = (f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh:.0f}" rx="10" fill="{t["panel"]}" stroke="{t["rule"]}"/>'
             f'<path d="M{wx} {wy + bar}h{ww}" stroke="{t["rule"]}"/>')
    # Animations only hide things briefly (fill-mode backwards): without animation support the card is complete.
    style = (f".typer{{animation:type .5s steps(9,end) .25s backwards}}"
             f"@keyframes type{{from{{width:0}}to{{width:{9 * cw:.1f}px}}}}"
             ".out{animation:hide .85s backwards}@keyframes hide{from,to{opacity:0}}"
             ".cursor{animation:blink 1.1s steps(1) 1s infinite}@keyframes blink{50%{opacity:0}}"
             "@media (prefers-reduced-motion:reduce){.typer,.out,.cursor{animation:none}}")
    body = frame + "".join(top) + f'<g class="out">{a}{hd}{f}</g>' + tail
    return svg(W, wy + wh + 16, slug, t, body, style)


def editorial(theme, narrow):
    t, slug = THEMES[theme], f"portrait-{theme}{'-n' if narrow else ''}"
    cols = 96
    p = portrait(cols, theme == "dark")
    if narrow:
        W, ps, fs = 560, 5.2, 16
        a, ah = art((W - cols * ps * CHAR_W) / 2, 36, p, ps, t, graded=True)
        y = 36 + ah + 58
        name = (text(32, y, NAME, 40, t["ink"], 700) + text(32, y + 32, TAGLINE, 16, t["muted"]))
        f, fh = facts(32, y + 84, fs, t)
        return svg(W, fh + 30, slug, t, a + name + f)
    W, ps, fs = 1000, 6.2, 16
    a, ah = art(36, 40, p, ps, t, graded=True)
    ix = 36 + cols * ps * CHAR_W + 52
    name = text(ix, 96, NAME, 46, t["ink"], 700) + text(ix, 130, TAGLINE, 16, t["muted"])
    f, fh = facts(ix, 186, fs, t)
    return svg(W, max(40 + ah, fh) + 30, slug, t, a + name + f)


VARIANTS = {"neofetch": neofetch, "terminal": terminal, "portrait": editorial}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "assets")
    ap.add_argument("--refresh-portrait", action="store_true")
    a = ap.parse_args()
    if a.refresh_portrait:  # rebuild into place; a failed fetch leaves the old files untouched
        for f in TOOLS.glob("portrait-*.txt"):
            cols, bright = f.stem.split("-")[1], f.stem.endswith("-bright")
            tmp = f.with_suffix(".new")
            make_portrait(int(cols), bright, tmp)
            tmp.replace(f)
    a.out.mkdir(parents=True, exist_ok=True)
    for name in (VARIANTS if a.all else [CHOSEN]):
        for theme in (THEMES if a.all else ["dark"]):
            for narrow in (False, True):
                suffix = f"{theme}{'-narrow' if narrow else ''}.svg"
                fn = a.out / (f"{name}-{suffix}" if a.all else f"card-{suffix}")
                fn.write_text(VARIANTS[name](theme, narrow))
                print("wrote", fn)


if __name__ == "__main__":
    main()
