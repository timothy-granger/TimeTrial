"""
Markdown to print-ready HTML converter.
Usage: python md_to_html.py <input.md> [output.html]

Open the HTML in a browser, then Ctrl+P -> Save as PDF.
"""
import sys
import os
import markdown


CSS = """
@media print {
    body { margin: 0; }
    h1, h2, h3 { page-break-after: avoid; }
    table, blockquote, pre { page-break-inside: avoid; }
}

body {
    font-family: 'Segoe UI', Calibri, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #1a1a1a;
    max-width: 960px;
    margin: 40px auto;
    padding: 0 40px;
    background: #fff;
}

h1 {
    font-size: 28px;
    color: #1a1a2e;
    border-bottom: 3px solid #16213e;
    padding-bottom: 8px;
    margin-top: 32px;
}

h2 {
    font-size: 22px;
    color: #16213e;
    border-bottom: 2px solid #0f3460;
    padding-bottom: 6px;
    margin-top: 28px;
}

h3 {
    font-size: 17px;
    color: #0f3460;
    margin-top: 20px;
}

/* --- TABLES --- */
table {
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 13px;
    width: 100%;
    border: 2px solid #16213e;
}

thead th {
    background-color: #16213e;
    color: #ffffff;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid #16213e;
    white-space: nowrap;
}

tbody td {
    padding: 8px 12px;
    border: 1px solid #c8d6e5;
    vertical-align: top;
}

tbody tr:nth-child(even) {
    background-color: #f0f4f8;
}

tbody tr:nth-child(odd) {
    background-color: #ffffff;
}

tbody tr:hover {
    background-color: #dbe6f0;
}

/* Bold text in table cells */
td strong, th strong {
    color: inherit;
}

/* --- BLOCKQUOTES --- */
blockquote {
    border-left: 4px solid #0f3460;
    margin: 16px 0;
    padding: 12px 20px;
    background-color: #f0f4f8;
    color: #333;
    font-style: italic;
}

blockquote strong {
    font-style: normal;
    color: #16213e;
}

blockquote ol, blockquote ul {
    margin: 8px 0;
}

/* --- CODE --- */
code {
    background-color: #eef2f7;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12.5px;
    color: #c0392b;
}

pre {
    background-color: #f5f7fa;
    padding: 16px;
    border: 1px solid #d5dce6;
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre-wrap;
}

pre code {
    background: none;
    padding: 0;
    color: #1a1a1a;
}

/* --- LISTS --- */
ul, ol {
    margin: 8px 0;
    padding-left: 28px;
}

li {
    margin-bottom: 4px;
}

/* --- HORIZONTAL RULES --- */
hr {
    border: none;
    border-top: 2px solid #d5dce6;
    margin: 24px 0;
}

/* --- MISC --- */
strong {
    color: #16213e;
}

em {
    color: #444;
}

a {
    color: #0f3460;
}

p {
    margin: 10px 0;
}

/* Footer */
.footer-note {
    text-align: center;
    color: #888;
    font-size: 12px;
    margin-top: 40px;
    border-top: 1px solid #ddd;
    padding-top: 12px;
}
"""


def md_to_html(md_path, html_path=None):
    if html_path is None:
        html_path = os.path.splitext(md_path)[0] + ".html"

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{os.path.splitext(os.path.basename(md_path))[0]}</title>
    <style>{CSS}</style>
</head>
<body>
{html_body}
<div class="footer-note">
    Print this page (Ctrl+P) and select "Save as PDF" for best results.
</div>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML created: {html_path}")
    return html_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python md_to_html.py <input.md> [output.html]")
        sys.exit(1)

    md_file = sys.argv[1]
    html_file = sys.argv[2] if len(sys.argv) > 2 else None
    md_to_html(md_file, html_file)
