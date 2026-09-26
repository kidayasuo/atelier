#!/usr/bin/env python3
"""Build the GitHub Pages site: copy the repo and render every .md as a phone-friendly .html.

Usage: python tools/build_site.py <repo_dir> <out_dir>

- foo/bar.md      -> foo/bar.html   (skipped with a warning if foo/bar.html is committed)
- foo/README.md   -> foo/index.html (only when foo/index.html does not exist)
- Optional first-line comment in a .md:  <!-- eyebrow: デザ建 雪の旅 -->
  sets the small line above the title. It is invisible on github.com.
- A short first paragraph right under the "# Title" becomes the subtitle.
- Relative links to .md files are rewritten to the generated .html.
"""
import html
import os
import re
import shutil
import sys

import markdown
from markdown.extensions.toc import slugify_unicode

SKIP_DIRS = {".git", ".github", "tools", "_site"}
SKIP_FILES = {"_config.yml", ".gitignore"}

CSS = """
:root{--bg:#fff;--text:#1d2126;--muted:#5b6570;--accent:#4f93d6;--accent-strong:#2f78c2;--rule:#dbe6f1;--chip:#eef5fc;--th:#f3f7fb;color-scheme:light}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#14181d;--text:#e6eaef;--muted:#9aa6b2;--accent:#7fb6ec;--accent-strong:#9cc7f2;--rule:#2a3440;--chip:#1c2631;--th:#1a222c}}
*,*::before,*::after{box-sizing:border-box}
html{scroll-padding-top:16px}
body{margin:0;background:var(--bg);color:var(--text);font-family:"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP",system-ui,sans-serif;font-size:16px;line-height:1.8;padding:32px 18px 64px;padding-top:calc(32px + env(safe-area-inset-top,0px))}
.page{max-width:720px;margin:0 auto}
header{text-align:center;margin-bottom:24px}
.eyebrow{font-size:13px;letter-spacing:.12em;color:var(--muted);margin:0 0 4px}
h1{color:var(--accent);font-size:clamp(24px,6vw,30px);line-height:1.4;margin:0;text-wrap:balance}
.sub{color:var(--muted);font-size:13px;margin-top:6px}
details.toc{background:var(--chip);border-radius:8px;padding:10px 16px;margin:0 0 28px}
details.toc summary{cursor:pointer;font-weight:700;color:var(--accent-strong)}
details.toc ul{list-style:none;padding:0;margin:8px 0 4px;columns:2;column-gap:24px}
details.toc li{break-inside:avoid;font-size:14px;line-height:1.9}
@media (max-width:520px){details.toc ul{columns:1}}
h2{color:var(--accent);font-size:21px;line-height:1.5;margin:48px 0 14px;padding-bottom:6px;border-bottom:2px solid var(--rule);text-wrap:balance}
h3{font-size:17px;line-height:1.5;margin:28px 0 8px;text-wrap:balance}
p{margin:0 0 12px}
a{color:var(--accent-strong);overflow-wrap:anywhere}
ul,ol{padding-left:1.4em;margin:0 0 14px}
li{margin:2px 0}
blockquote{margin:0 0 16px;padding:10px 16px;border-left:3px solid var(--accent);background:var(--chip);border-radius:0 6px 6px 0;font-size:15px}
blockquote p:last-child,blockquote ul:last-child{margin-bottom:0}
.table-wrap{overflow-x:auto;margin:0 0 18px;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;font-size:13.5px;line-height:1.6;min-width:100%}
th,td{border:1px solid var(--rule);padding:6px 9px;text-align:left;vertical-align:top}
th{background:var(--th);font-weight:700;white-space:nowrap}
td{min-width:5em}
strong{font-weight:700}
.back{position:fixed;right:14px;bottom:calc(14px + env(safe-area-inset-bottom,0px));background:var(--accent);color:#fff;text-decoration:none;border-radius:999px;padding:8px 14px;font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,.15)}
"""

FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap">'
)


def autolink(h):
    """Link bare URLs that are not already inside a tag or <a>."""
    parts = re.split(r"(<a\b.*?</a>|<[^>]+>)", h, flags=re.S)
    for i, p in enumerate(parts):
        if p.startswith("<"):
            continue
        parts[i] = re.sub(
            r"(https?://[^\s<　）)」、。]+)",
            lambda m: f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}</a>',
            p,
        )
    return "".join(parts)


def render(md):
    eyebrow = ""
    m = re.match(r"\s*<!--\s*eyebrow:\s*(.*?)\s*-->\s*\n", md)
    if m:
        eyebrow = m.group(1)
        md = md[m.end():]

    title = ""
    m = re.match(r"\s*#\s+(.+)\n", md)
    if m:
        title = m.group(1).strip()
        md = md[m.end():]

    md = re.sub(r"(?m)^---\s*$", "", md)  # horizontal rules
    # python-markdown needs a blank line before a table or list that follows a paragraph line
    md = re.sub(r"(?m)^([^\n|>#\-\s][^\n]*)\n(\|)", r"\1\n\n\2", md)
    md = re.sub(r"(?m)^([^\n|>\-\s\d][^\n]*)\n(- |\d+\. )", r"\1\n\n\2", md)
    # relative links to .md -> .html
    md = re.sub(r"\]\((?!https?://)([^)\s]+?)\.md(#[^)]*)?\)", r"](\1.html\2)", md)

    conv = markdown.Markdown(
        extensions=["tables", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-2", "slugify": slugify_unicode}},
    )
    body = conv.convert(md)
    n_h2 = body.count("<h2")
    toc_inner = re.sub(r'^<div class="toc">|</div>\s*$', "", conv.toc.strip())

    body = autolink(body)
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")

    sub = ""
    m = re.match(r"\s*<p>(.*?)</p>", body, re.S)
    if m and len(re.sub(r"<[^>]+>", "", m.group(1))) <= 80 and title:
        sub = m.group(1)
        body = body[m.end():]

    head_title = html.escape(title or "atelier")
    parts = [
        "<!doctype html>",
        '<html lang="ja">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
        f"<title>{head_title}</title>",
        '<meta name="robots" content="noindex">',
        FONTS,
        f"<style>{CSS}</style>",
        "</head>",
        "<body>",
        '<div class="page" id="top">',
    ]
    if title:
        parts.append("<header>")
        if eyebrow:
            parts.append(f'<p class="eyebrow">{html.escape(eyebrow)}</p>')
        parts.append(f"<h1>{html.escape(title)}</h1>")
        if sub:
            parts.append(f'<p class="sub">{sub}</p>')
        parts.append("</header>")
    with_toc = n_h2 >= 3
    if with_toc:
        parts.append(f'<details class="toc" open><summary>目次</summary>\n{toc_inner}\n</details>')
    parts.append(body)
    parts.append("</div>")
    if with_toc:
        parts.append('<a class="back" href="#top">目次へ</a>')
    parts += ["</body>", "</html>", ""]
    return "\n".join(parts)


def main(repo, out):
    if os.path.exists(out):
        shutil.rmtree(out)
    committed = set()
    mds = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        rel = os.path.relpath(root, repo)
        for f in files:
            if f in SKIP_FILES:
                continue
            src = os.path.join(root, f)
            dst = os.path.normpath(os.path.join(out, rel, f))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            committed.add(os.path.normpath(os.path.join(rel, f)))
            if f.endswith(".md"):
                mds.append(os.path.normpath(os.path.join(rel, f)))

    for rel in mds:
        d, f = os.path.split(rel)
        target = os.path.join(d, "index.html") if f == "README.md" else rel[:-3] + ".html"
        if target in committed:
            print(f"skip   {rel}  ({target} is committed)")
            continue
        with open(os.path.join(repo, rel), encoding="utf-8") as fh:
            page = render(fh.read())
        with open(os.path.join(out, target), "w", encoding="utf-8") as fh:
            fh.write(page)
        print(f"build  {rel} -> {target}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
