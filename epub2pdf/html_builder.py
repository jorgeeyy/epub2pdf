from pathlib import Path
from bs4 import BeautifulSoup
from .styles import PRINT_CSS


def process_footnotes(html):
    soup = BeautifulSoup(html, "lxml")

    for a in soup.find_all("a", href=True):
        if a["href"].startswith("#fn"):
            a["class"] = a.get("class", []) + ["footnote"]

    return str(soup)


def resolve_images(html, content_dir):
    """Resolve relative image src paths to absolute file paths."""
    if content_dir is None:
        return html

    soup = BeautifulSoup(html, "lxml")
    content_path = Path(content_dir)

    for img in soup.find_all("img", src=True):
        src = img["src"]
        # Skip already-absolute URLs (http, data URIs, etc.)
        if src.startswith(("http://", "https://", "data:")):
            continue
        # Resolve the relative path against the content directory
        abs_path = (content_path / src).resolve()
        if abs_path.exists():
            img["src"] = str(abs_path)

    # Also handle SVG <image> tags with xlink:href
    for img in soup.find_all("image"):
        href = img.get("xlink:href") or img.get("href")
        if not href:
            continue
        if href.startswith(("http://", "https://", "data:")):
            continue
        abs_path = (content_path / href).resolve()
        if abs_path.exists():
            path_str = str(abs_path)
            if img.get("xlink:href"):
                img["xlink:href"] = path_str
            else:
                img["href"] = path_str

    return str(soup)


def build_html(chapters, content_dir=None):
    body = "".join(chapters)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{PRINT_CSS}
</style>
</head>
<body>
{body}
</body>
</html>
"""
    # Resolve image paths before returning
    if content_dir is not None:
        html = resolve_images(html, content_dir)

    return html
