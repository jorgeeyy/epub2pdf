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


def _add_chapter_ids(chapter_parts):
    """Add id='chapter-N' to the first h1/h2 in each chapter part.

    Also builds a mapping from filename stems to chapter anchor IDs,
    so we can rewrite TOC links.
    """
    stem_to_anchor = {}

    for i, (body_html, source_path) in enumerate(chapter_parts):
        soup = BeautifulSoup(body_html, "lxml")

        # Find the first h1 or h2 to use as the chapter anchor
        heading = soup.find("h1") or soup.find("h2")
        if heading:
            anchor_id = f"chapter-{i}"
            existing_id = heading.get("id")
            if existing_id:
                anchor_id = existing_id
            else:
                heading["id"] = anchor_id

            # Map the source filename stem to this anchor
            if source_path:
                stem = Path(source_path).stem
                stem_to_anchor[stem] = anchor_id

        # Update the body HTML with the modified soup
        chapter_parts[i] = (str(soup), source_path)

    return chapter_parts, stem_to_anchor


def _build_toc_html(toc_entries, stem_to_anchor):
    """Build an HTML TOC block with rewritten in-page anchor links.

    Args:
        toc_entries: list of (title, href) from the EPUB nav file
        stem_to_anchor: mapping from filename stems to chapter anchor IDs
    """
    if not toc_entries:
        return ""

    toc_items = []
    for title, href in toc_entries:
        # Strip any fragment from the href
        href_stem = Path(href).stem if "#" not in href else Path(href.split("#")[0]).stem

        # Look up the anchor ID for this chapter
        anchor = stem_to_anchor.get(href_stem)
        if anchor:
            toc_items.append(f'<li><a href="#{anchor}">{title}</a></li>')

    if not toc_items:
        return ""

    items_html = "\n".join(toc_items)
    return f"""
<nav epub:type="toc" id="toc" role="doc-toc">
<h1>Table of Contents</h1>
<ol>
{items_html}
</ol>
</nav>
"""


def build_html(chapters, epub_root=None, toc=None):
    """Build a complete HTML document from chapter body strings.

    Args:
        chapters: list of (body_html, source_path) tuples.
        epub_root: fallback directory for resolving images when source_path is None.
        toc: list of (title, href) TOC entries from the EPUB nav file.
    """
    # Add chapter IDs and build stem-to-anchor mapping
    chapters, stem_to_anchor = _add_chapter_ids(list(chapters))

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

    body_content = "".join(soup_parts)

    # Build and prepend TOC if available
    toc_html = _build_toc_html(toc or [], stem_to_anchor)

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
{toc_html}
{body_content}
</body>
</html>
"""
