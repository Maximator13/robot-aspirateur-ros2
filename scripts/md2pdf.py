"""Convertit des fichiers Markdown (avec diagrammes Mermaid) en PDF via Chrome sous Windows (WSL).

Usage : python3 md2pdf.py <dossier_sortie> <fichier.md> <titre> [<fichier.md> <titre> ...]
Rendu : marked (Markdown) et mermaid (diagrammes), chargés depuis jsdelivr ; impression par Chrome headless.
"""
import json
import os
import subprocess
import sys
import tempfile

CHROME = '/mnt/c/Program Files/Google/Chrome/Application/chrome.exe'
DISTRO = os.environ.get('WSL_DISTRO_NAME', 'Ubuntu-22.04')
TEMPLATE = """<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{title}</title>
<base href="{base}"><style>
@page {{ size: A4; margin: 16mm 14mm; }}
body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1d2433; }}
h1 {{ font-size: 20pt; border-bottom: 2px solid #1F5F99; padding-bottom: 4px; }}
h2 {{ font-size: 15pt; color: #1F5F99; margin-top: 22px; break-after: avoid; }}
h3 {{ font-size: 12pt; break-after: avoid; }}
table {{ border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9.5pt; }}
th, td {{ border: 1px solid #c9ced8; padding: 4px 6px; vertical-align: top; text-align: left; }}
th {{ background: #e9edf3; }} tr {{ break-inside: avoid; }}
code {{ font-family: Consolas, monospace; font-size: 9pt; background: #f1f3f6; padding: 0 3px; }}
pre {{ background: #f1f3f6; padding: 8px; white-space: pre-wrap; font-size: 8.5pt; break-inside: avoid; }}
pre code {{ background: none; }} img {{ max-width: 100%; }}
.mermaid {{ text-align: center; break-inside: avoid; margin: 10px 0; }}
</style></head><body><div id="c"></div>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
const md = {md};
const r = new marked.Renderer(); const baseCode = r.code.bind(r);
r.code = function(code, lang) {{
  if (lang === 'mermaid') return '<div class="mermaid">' + code.replace(/</g, '&lt;') + '</div>';
  return baseCode(code, lang); }};
document.getElementById('c').innerHTML = marked.parse(md, {{renderer: r}});
mermaid.initialize({{startOnLoad: false, theme: 'neutral'}}); mermaid.run({{querySelector: '.mermaid'}});
</script></body></html>"""


def win(path):
    """Chemin Linux -> chemin Windows vu depuis Chrome (\\\\wsl.localhost\\...)."""
    return '\\\\wsl.localhost\\' + DISTRO + path.replace('/', '\\')


def url(path):
    return 'file://wsl.localhost/' + DISTRO + path


def convert(out_dir, md_path, title):
    md_path = os.path.abspath(md_path)
    with open(md_path, encoding='utf-8') as f:
        md = f.read()
    html = TEMPLATE.format(title=title, base=url(os.path.dirname(md_path)) + '/', md=json.dumps(md))
    tmp = tempfile.mkdtemp(dir=os.path.expanduser('~'))  # visible depuis Windows
    html_path = os.path.join(tmp, 'page.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    pdf = os.path.join(os.path.abspath(out_dir), title + '.pdf')
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                    '--virtual-time-budget=20000', '--print-to-pdf=' + win(pdf), url(html_path)],
                   timeout=180, capture_output=True)
    os.remove(html_path)
    os.rmdir(tmp)
    print(pdf, os.path.exists(pdf))


if __name__ == '__main__':
    args = sys.argv[2:]
    for i in range(0, len(args), 2):
        convert(sys.argv[1], args[i], args[i + 1])
