import zipfile
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import xml.etree.ElementTree as ET
import warnings
import logging

logger = logging.getLogger(__name__)

# Suppress BeautifulSoup warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class InvalidEPUBError(Exception):
    """Raised when the input file is not a valid EPUB."""


def validate_epub(epub_path):
    """Validate that the file exists and is a valid ZIP/EPUB."""
    path = Path(epub_path)
    if not path.exists():
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")
    if not path.suffix.lower() == ".epub":
        raise InvalidEPUBError(f"File is not an EPUB: {epub_path}")
    if not zipfile.is_zipfile(path):
        raise InvalidEPUBError(f"File is not a valid ZIP archive: {epub_path}")
    return path


def extract_epub(epub_path, workdir):
    with zipfile.ZipFile(epub_path) as z:
        z.extractall(workdir)


def _read_text(path):
    """Read text file with UTF-8 fallback to latin-1."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed for %s, falling back to latin-1", path)
        return path.read_text(encoding="latin-1")


def get_opf_path(workdir):
    """Find the OPF file path from META-INF/container.xml"""
    container_path = Path(workdir) / "META-INF" / "container.xml"
    if not container_path.exists():
        return None

    tree = ET.parse(container_path)
    root = tree.getroot()

    # Handle namespace
    ns = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
    rootfile = root.find('.//container:rootfile', ns)

    if rootfile is not None:
        return Path(workdir) / rootfile.get('full-path')
    return None


def get_spine_order(opf_path):
    """Extract the reading order from the OPF spine"""
    tree = ET.parse(opf_path)
    root = tree.getroot()

    # Common OPF namespace
    ns = {'opf': 'http://www.idpf.org/2007/opf'}

    # Get manifest (id -> href mapping)
    manifest = {}
    for item in root.findall('.//opf:manifest/opf:item', ns):
        item_id = item.get('id')
        href = item.get('href')
        if item_id and href:
            manifest[item_id] = href

    # If no namespace found, try without namespace
    if not manifest:
        for item in root.findall('.//manifest/item'):
            item_id = item.get('id')
            href = item.get('href')
            if item_id and href:
                manifest[item_id] = href

    # Get spine order
    spine_items = []
    for itemref in root.findall('.//opf:spine/opf:itemref', ns):
        idref = itemref.get('idref')
        if idref and idref in manifest:
            spine_items.append(manifest[idref])

    # If no namespace found, try without namespace
    if not spine_items:
        for itemref in root.findall('.//spine/itemref'):
            idref = itemref.get('idref')
            if idref and idref in manifest:
                spine_items.append(manifest[idref])

    return spine_items


def _parse_chapter(chapter_path):
    """Parse a chapter XHTML file and return its body HTML."""
    soup = BeautifulSoup(_read_text(chapter_path), "lxml")
    if soup.body:
        return str(soup.body)
    return None


def _find_nav_file(workdir):
    """Find the EPUB navigation (nav) file."""
    workdir_path = Path(workdir)

    # EPUB 3: look for nav file referenced in OPF
    opf_path = get_opf_path(workdir)
    if opf_path and opf_path.exists():
        try:
            tree = ET.parse(opf_path)
            root = tree.getroot()
            ns = {'opf': 'http://www.idpf.org/2007/opf',
                  'epub': 'http://www.idpf.org/2007/ops'}

            # Look for item with properties="nav"
            for item in root.findall('.//opf:manifest/opf:item', ns):
                if 'nav' in (item.get('properties') or ''):
                    href = item.get('href')
                    if href:
                        nav_path = (opf_path.parent / href).resolve()
                        if nav_path.exists():
                            return nav_path
        except Exception:
            pass

    # Fallback: find any file with "nav" in the name
    for nav in workdir_path.rglob("*nav*.xhtml"):
        return nav
    for nav in workdir_path.rglob("*nav*.html"):
        return nav

    # EPUB 2 fallback: look for NCX file
    for ncx in workdir_path.rglob("*.ncx"):
        return ncx

    return None


def _parse_nav_toc(nav_path):
    """Parse the navigation file and return flat TOC entries.

    Returns list of (title, href) tuples where href is relative to the
    nav file's directory.
    """
    content = _read_text(nav_path)
    soup = BeautifulSoup(content, "lxml")

    toc_entries = []

    # Check if it's an EPUB 3 nav file or EPUB 2 NCX
    if nav_path.suffix.lower() == ".ncx":
        # NCX format
        for navpoint in soup.find_all("navpoint"):
            label = navpoint.find("navlabel")
            content_tag = navpoint.find("content")
            if label and content_tag:
                text = label.get_text(strip=True)
                src = content_tag.get("src", "")
                if text and src:
                    toc_entries.append((text, src))
    else:
        # EPUB 3 nav format: find <nav epub:type="toc">
        toc_nav = soup.find("nav", attrs={"epub:type": "toc"})
        if not toc_nav:
            toc_nav = soup.find("nav", id="toc")
        if not toc_nav:
            toc_nav = soup.find("nav")

        if toc_nav:
            # Only get top-level <li> entries (skip nested sub-chapter lists)
            top_ol = toc_nav.find("ol")
            if top_ol:
                for li in top_ol.find_all("li", recursive=False):
                    a = li.find("a", href=True)
                    if a:
                        text = a.get_text(strip=True)
                        href = a["href"]
                        if text and href:
                            toc_entries.append((text, href))

    return toc_entries


def _parse_ncx_toc(ncx_path):
    """Parse an NCX file for TOC entries (EPUB 2 fallback)."""
    content = _read_text(ncx_path)
    soup = BeautifulSoup(content, "xml")

    toc_entries = []
    for navpoint in soup.find_all("navpoint"):
        label = navpoint.find("navlabel")
        content_tag = navpoint.find("content")
        if label and content_tag:
            text = label.get_text(strip=True)
            src = content_tag.get("src", "")
            if text and src:
                toc_entries.append((text, src))

    return toc_entries


def get_chapters(workdir):
    """Extract chapters in the correct reading order from EPUB spine.

    Returns:
        tuple: (chapters, epub_root, toc) where chapters is a list of
               (body_html, source_path) tuples, epub_root is the EPUB root
               directory, and toc is a list of (title, href) TOC entries.
    """
    workdir_path = Path(workdir)

    # Parse TOC from nav/NCX file
    toc = []
    nav_path = _find_nav_file(workdir)
    if nav_path:
        try:
            if nav_path.suffix.lower() == ".ncx":
                toc = _parse_ncx_toc(nav_path)
            else:
                toc = _parse_nav_toc(nav_path)
        except Exception as e:
            logger.warning("Failed to parse TOC: %s", e)

    # Try to get proper reading order from OPF
    opf_path = get_opf_path(workdir)

    if opf_path and opf_path.exists():
        try:
            spine_order = get_spine_order(opf_path)
            opf_dir = opf_path.parent

            chapters = []
            for href in spine_order:
                # Resolve relative path from OPF location
                chapter_path = (opf_dir / href).resolve()

                if chapter_path.exists():
                    try:
                        body = _parse_chapter(chapter_path)
                        if body:
                            chapters.append((body, chapter_path))
                    except Exception as e:
                        logger.warning("Skipping chapter %s: %s", chapter_path, e)
                else:
                    logger.warning("Chapter file not found, skipping: %s", chapter_path)

            if chapters:
                return chapters, workdir_path, toc
        except Exception as e:
            logger.warning("OPF/spine parsing failed, falling back to alphabetical order: %s", e)

    # Fallback to alphabetical sorting if OPF parsing fails
    xhtml_files = sorted(workdir_path.rglob("*.xhtml"))
    if not xhtml_files:
        xhtml_files = sorted(workdir_path.rglob("*.html"))

    chapters = []
    for file in xhtml_files:
        try:
            body = _parse_chapter(file)
            if body:
                chapters.append((body, file))
        except Exception as e:
            logger.warning("Skipping chapter %s: %s", file, e)

    return chapters, workdir_path, toc
