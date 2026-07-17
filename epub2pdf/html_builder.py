import re
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from .styles import PRINT_CSS

logger = logging.getLogger(__name__)

FOOTNOTE_PATTERN = re.compile(r"#(fn|footnote|note|_ftn|cite)[\d\-_]", re.IGNORECASE)


def _resolve_images_in_soup(soup, base_dir):
    """Resolve relative image src paths to absolute file paths in a parsed soup."""
    if base_dir is None:
        return

    content_path = Path(base_dir)

    for img in soup.find_all("img", src=True):
        src = img["src"]
        if src.startswith(("http://", "https://", "data:")):
            continue
        abs_path = (content_path / src).resolve()
        if abs_path.exists():
            img["src"] = str(abs_path)
        else:
            logger.warning("Image not found in EPUB: %s", src)

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
        else:
            logger.warning("Image not found in EPUB: %s", href)


def build_html(chapters, epub_root=None):
    """Build a complete HTML document from chapter body strings.

    Args:
        chapters: list of (body_html, source_path) tuples. source_path is the
                  Path to the chapter file, used to resolve relative image paths.
                  Can also be plain strings for backward compatibility.
        epub_root: fallback directory for resolving images when source_path is None.
    """
    soup_parts = []
    for item in chapters:
        if isinstance(item, tuple):
            body_html, source_path = item
        else:
            body_html, source_path = item, None

        chapter_soup = BeautifulSoup(body_html, "lxml")

        # Resolve images relative to the chapter file's own directory
        base_dir = None
        if source_path is not None:
            base_dir = Path(source_path).parent
        elif epub_root is not None:
            base_dir = Path(epub_root)

        _resolve_images_in_soup(chapter_soup, base_dir)

        # Process footnotes
        for a in chapter_soup.find_all("a", href=True):
            if FOOTNOTE_PATTERN.search(a["href"]):
                a["class"] = a.get("class", []) + ["footnote"]

        soup_parts.append(str(chapter_soup))

    body = "".join(soup_parts)

    return f"""
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
