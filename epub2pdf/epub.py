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


def get_chapters(workdir):
    """Extract chapters in the correct reading order from EPUB spine.

    Returns:
        tuple: (chapters, epub_root) where chapters is a list of
               (body_html, source_path) tuples, and epub_root is the
               EPUB root directory (used as fallback for image resolution).
    """
    workdir_path = Path(workdir)

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
                return chapters, workdir_path
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

    return chapters, workdir_path
