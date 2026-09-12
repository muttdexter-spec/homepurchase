#!/usr/bin/env python3
"""Freeze the page chrome as two templates, one per build.

Reads the two built pages at the repo root (full.html, mobile.html) and writes
page_full.tpl.html and page_mobile.tpl.html beside this script. Every region the
model produces is replaced by a {{PLACEHOLDER}}; everything else, which is the
design (three or four style blocks, the scripts, the control strip, the jump bar,
the phone-only CSS, the 'Under the hood' tail), is kept byte for byte.

This is how build_walkthrough.py can regenerate both builds without the design
being retyped, and it is why a regenerated page differs from the previous one only
in data. NOT part of refresh.sh: run it by hand only after a deliberate change to
the chrome, and check the diff.

Usage: python3 make_page_templates.py
"""
import os, re, sys

R = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(R, "..")

def one(pat, s, repl, label, flags=re.S):
    """Replace exactly one match. Anything else is a template that would silently
    drop content, so it is an error."""
    n = len(re.findall(pat, s, flags))
    if n != 1:
        print(f"  FAIL {label}: {n} matches", file=sys.stderr); sys.exit(1)
    return re.sub(pat, lambda m: repl, s, count=1, flags=flags)

def s_end(h, marker):
    """Index just past a marker that must appear exactly once."""
    if h.count(marker) != 1:
        print(f"  FAIL marker {marker!r}: {h.count(marker)} matches", file=sys.stderr); sys.exit(1)
    return h.index(marker) + len(marker)

def build(variant):
    src = os.path.join(ROOT, f"{variant}.html")
    h = open(src, encoding="utf-8").read()
    # ---- the card stack: the opening div to the last </article>
    o = '<div class="lots" id="lots">'
    a = h.index(o) + len(o); b = h.rindex("</article>") + len("</article>")
    h = h[:a] + "{{LOTS}}" + h[b:]
    # ---- the whole table (not the calculator table, which the script fills at run time)
    t0 = h.index('<table class="big"><thead><tr>')
    t1 = h.index("</tr></thead>", t0); b0 = h.index("<tbody>", t1) + len("<tbody>")
    b1 = h.index("</tbody></table>", b0)
    h = h[:t0 + len('<table class="big"><thead><tr>')] + "{{THEAD}}" + h[t1:b0] + "{{TBODY}}" + h[b1:]
    # ---- masthead copy
    h = one(r'(?<=<p class="kicker">).*?(?=</p>)', h, "{{KICKER}}", "kicker")
    h = one(r'(?<=<p class="standfirst">).*?(?=</p>)', h, "{{STANDFIRST}}", "standfirst")
    h = one(r'(?<=<div class="mast-meta">).*?(?=</div>)', h, "{{MASTMETA}}", "mast-meta")
    # ---- the two blocks of running copy the model's wording lives in
    h = one(r'(?<=<p class="howto">).*?(?=</p>)', h, "{{HOWTO}}", "howto")
    h = one(r'(?<=<dl class="glossary">).*?(?=</dl>)', h, "{{GLOSSARY}}", "glossary")
    # ---- the two section-head paragraphs that describe the rank
    h = one(r'(?<=<h2>The whole table</h2>\n    <p>).*?(?=</p>)', h, "{{TABLEINTRO}}", "table intro")
    h = one(r'(?<=<h2>House by house</h2>\n    <p>).*?(?=</p>)', h, "{{CARDSINTRO}}", "cards intro")
    # ---- a slot for the frontier chart, at the end of the table's section-head
    a = s_end(h, "{{TABLEINTRO}}</p>"); b = h.index("\n  </div>\n  <div class=\"tablewrap", a)
    h = h[:a] + "{{FRONTIERCHART}}" + h[b:]
    # ---- a slot for the hold toggle, at the end of the control strip
    a = s_end(h, '<span class="sr-pill" id="sr-pill"></span>'); b = h.index("\n  </div>\n", a)
    h = h[:a] + "{{HOLDTOGGLE}}" + h[b:]
    # ---- the phone build's mini table (the desktop table is display:none there)
    if '<ul class="minitable">' in h:
        a = s_end(h, '<ul class="minitable">'); b = h.index("\n  </ul>", a)
        h = h[:a] + "{{MINITABLE}}" + h[b:]
    # ---- jump list (full parks it in a float, mobile puts it in a bar)
    m = re.search(r'(<select id="jump"[^>]*>)([^\0]*?)(</select>)', h)
    if not m: print("  FAIL jump select", file=sys.stderr); sys.exit(1)
    h = h[:m.start(2)] + "{{JUMPOPTS}}" + h[m.end(2):]
    # ---- colophon
    h = one(r'(?<=<p class="colophon">).*?(?=</p>)', h, "{{COLOPHON}}", "colophon")
    # ---- script data literals
    for name, ph in (("HOUSES", "{{HOUSES}}"), ("RESERVE", "{{RESERVE}}"), ("SHOW_DATA", "{{SHOW_DATA}}")):
        pat = r"(?<=\nconst " + name + r" = )[^\n]*?(?=;\n)"
        if re.search(pat, h):
            h = one(pat, h, ph, "const " + name)
    out = os.path.join(R, f"page_{variant}.tpl.html")
    open(out, "w", encoding="utf-8").write(h)
    print(f"  wrote {os.path.basename(out)} {len(h):,} bytes; placeholders:",
          ", ".join(sorted(set(re.findall(r"\{\{(\w+)\}\}", h)))))

if __name__ == "__main__":
    for v in ("full", "mobile"):
        build(v)
