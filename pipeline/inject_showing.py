#!/usr/bin/env python3
"""Graft the showing record onto an already-built walkthrough HTML.

The -full / -mobile deliverables were not produced by build_walkthrough.py in this folder, so the
record is injected rather than generated: this script edits any built page that has
<article class="lot" data-slug="..."> cards and a <p class="ask"> per card.

    python3 inject_showing.py ../deliverables/Walking-the-Shortlist-full.html [more.html ...]

Writes <name>.html in place (keeping a .orig.html beside it the first time) and also emits
<name>.artifact-src.html, body-only, for the Artifact tool.
Idempotent: a file that already carries the record is re-injected from its .orig.html.
"""
import json, csv, os, re, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import showing2 as SH

R = os.path.dirname(os.path.abspath(__file__))
OBS = {o["slug"]: o for o in json.load(open(os.path.join(R, "observations.json")))}
DET = json.load(open(os.path.join(R, "out", "detail.json")))
ROWS = list(csv.DictReader(open(os.path.join(R, "out", "decision.csv"))))
BY_ADDR = {r["address"]: r for r in ROWS}

def short(slug): return slug.split("-", 2)[-1]
def addr_short(a):
    return (a.split(",")[0].replace(" Crescent", " Cres").replace(" Avenue", " Ave").replace(" Drive", " Dr")
            .replace(" Court", " Ct").replace(" Road", " Rd").replace(" Boulevard", " Blvd").replace(" Place", " Pl")
            .title().replace("Mls", "MLS"))

K2SLUG = {short(s): s for s in OBS}

CARD_RE = re.compile(r'<article class="lot" data-slug="([^"]+)"')
CHECK_RE = re.compile(r'(<section class="check">.*?</section>)', re.S)
LI_RE = re.compile(r'<li><input type="checkbox"[^>]*><label[^>]*>(.*?)</label></li>', re.S)
ASK_RE = re.compile(r'(<p class="ask">.*?</p>)', re.S)


def card_spans(s):
    """(start, end) for every .lot article."""
    starts = [m.start() for m in CARD_RE.finditer(s)]
    out = []
    for i, a in enumerate(starts):
        b = starts[i + 1] if i + 1 < len(starts) else s.index("</article>", a) + len("</article>")
        out.append((a, b))
    return out


def inject(path):
    orig = re.sub(r'\.html$', '', path) + ".orig.html"
    src = orig if os.path.exists(orig) else path
    s = open(src, encoding="utf-8").read()
    if src == path and not os.path.exists(orig):
        open(orig, "w", encoding="utf-8").write(s)

    houses, done = {}, 0
    spans = card_spans(s)
    pieces, last = [], 0
    for a, b in spans:
        card = s[a:b]
        k = CARD_RE.match(card).group(1)
        slug = K2SLUG.get(k)
        if not slug:
            pieces.append(s[last:b]); last = b; continue
        o, d = OBS[slug], DET[slug]
        row = BY_ADDR[o["address"]]

        # the listing-specific checks: keep the full text as the read-only agenda, strip the boxes
        checks = []
        m = CHECK_RE.search(card)
        if m:
            block = m.group(1)
            checks = [html.unescape(re.sub(r"<[^>]+>", "", t)).strip() for t in LI_RE.findall(block)]
            plain = LI_RE.sub(lambda mm: "<li>" + mm.group(1) + "</li>", block)
            card = card.replace(block, plain)

        rec = SH.record_html(k, o, d, checks)
        card = ASK_RE.sub(lambda mm: mm.group(1) + "\n" + rec, card, count=1)
        card = card.replace(f'<article class="lot" data-slug="{k}"',
                            f'<article class="lot" id="sr-lot-{k}" data-slug="{k}"', 1)

        houses[k] = {"slug": slug, "name": addr_short(o["address"]), "psf": int(row["all_in_psf"]),
                     "rank": int(row["rank"]), "verdict": row["verdict"]}
        pieces.append(s[last:a] + card)
        last = b
        done += 1
    pieces.append(s[last:])
    s = "".join(pieces)

    # control bar after the masthead
    bar = SH.CONTROL_BAR.replace("{N}", str(len(houses)))
    i = s.index("</header>") + len("</header>")
    s = s[:i] + "\n" + bar + s[i:]

    qs = {k: {"opts": [{"v": op["v"], "patch": op["patch"]} for op in q["opts"]]} for k, q in SH.QS.items()}
    data = {"houses": houses, "walk": SH.WALK, "qs": qs}
    js = open(os.path.join(R, "showing2.js"), encoding="utf-8").read()
    tail = "<script>\nconst SHOW_DATA = " + json.dumps(data) + ";\n" + js + "\n</script>\n"

    s = s.replace("</head>", SH.CSS + "</head>", 1)
    s = s.replace("</body>", tail + "</body>", 1)

    open(path, "w", encoding="utf-8").write(s)

    # body-only copy for the Artifact tool: everything from <title> to </body>
    t = s[s.index("<title>"):s.index("</body>")]
    t = t.replace('<link rel="preconnect"', '<link rel="preconnect"')  # keep as-is; fonts are allowlisted
    art = re.sub(r'</head>\s*<body[^>]*>', "\n", t, count=1)
    open(re.sub(r'\.html$', '', path) + ".artifact-src.html", "w", encoding="utf-8").write(art)
    print(f"{os.path.basename(path)}: {done} cards, {len(s):,} bytes")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        inject(p)
