"""EPUB eBook reader support."""
import os
import zipfile
import xml.etree.ElementTree as ET
from core.config import COLORS

class EPUBReader:
    """Read EPUB files and extract chapters."""

    NS = {
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'xhtml': 'http://www.w3.org/1999/xhtml',
    }

    def __init__(self, filepath):
        self.filepath = filepath
        self.title = "Unknown"
        self.author = "Unknown"
        self.chapters = []
        self._parse()

    def _parse(self):
        if not os.path.exists(self.filepath):
            return

        with zipfile.ZipFile(self.filepath, 'r') as z:
            # Find container.xml
            container = ET.fromstring(z.read('META-INF/container.xml'))
            rootfile = container.find('.//{*}rootfile')
            if rootfile is None:
                return

            opf_path = rootfile.get('full-path')
            opf_dir = os.path.dirname(opf_path)

            # Parse OPF
            opf = ET.fromstring(z.read(opf_path))

            # Metadata
            metadata = opf.find('opf:metadata', self.NS)
            if metadata is not None:
                title_elem = metadata.find('dc:title', self.NS)
                if title_elem is not None:
                    self.title = title_elem.text or "Unknown"
                author_elem = metadata.find('dc:creator', self.NS)
                if author_elem is not None:
                    self.author = author_elem.text or "Unknown"

            # Spine (reading order)
            spine = opf.find('opf:spine', self.NS)
            manifest = opf.find('opf:manifest', self.NS)

            if spine is None or manifest is None:
                return

            # Build id -> href map
            id_to_href = {}
            for item in manifest.findall('opf:item', self.NS):
                item_id = item.get('id')
                href = item.get('href')
                if item_id and href:
                    id_to_href[item_id] = os.path.join(opf_dir, href).replace('\\', '/')

            # Get chapters in order
            for itemref in spine.findall('opf:itemref', self.NS):
                item_id = itemref.get('idref')
                if item_id in id_to_href:
                    href = id_to_href[item_id]
                    try:
                        content = z.read(href).decode('utf-8')
                        # Extract text content (simplified)
                        text = self._extract_text(content)
                        self.chapters.append({
                            'id': item_id,
                            'title': f"Chapter {len(self.chapters) + 1}",
                            'content': text,
                            'href': href,
                        })
                    except:
                        pass

    def _extract_text(self, html):
        """Simple HTML to text extraction."""
        # Remove scripts and styles
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def get_chapter(self, index):
        if 0 <= index < len(self.chapters):
            return self.chapters[index]
        return None


def scan_epubs(directory):
    """Scan directory for EPUB files."""
    epubs = []
    if not os.path.exists(directory):
        return epubs
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.lower().endswith('.epub'):
                path = os.path.join(root, f)
                try:
                    reader = EPUBReader(path)
                    epubs.append({
                        'id': path,
                        'title': reader.title,
                        'author': reader.author,
                        'path': path,
                        'chapters_count': len(reader.chapters),
                        'source': 'local_epub',
                    })
                except:
                    pass
    return epubs
