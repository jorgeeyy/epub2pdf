import zipfile
from pathlib import Path
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

def extract_epub(epub_path, workdir):
    with zipfile.ZipFile(epub_path) as z:
        z.extractall(workdir)

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

def get_chapters(workdir):
    """Extract chapters in the correct reading order from EPUB spine"""
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
                        soup = BeautifulSoup(chapter_path.read_text(encoding="utf-8"), "lxml")
                        if soup.body:
                            chapters.append(str(soup.body))
                    except Exception as e:
                        print(f"Warning: Could not read {chapter_path}: {e}")
            
            if chapters:
                return chapters
        except Exception as e:
            print(f"Warning: Could not parse OPF file: {e}")
    
    # Fallback to alphabetical sorting if OPF parsing fails
    print("Warning: Using alphabetical order (OPF parsing failed)")
    chapters = []
    for file in sorted(workdir_path.rglob("*.xhtml")):
        soup = BeautifulSoup(file.read_text(encoding="utf-8"), "lxml")
        if soup.body:
            chapters.append(str(soup.body))
    
    return chapters
