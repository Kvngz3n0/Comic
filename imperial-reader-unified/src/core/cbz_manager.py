"""CBZ (Comic Book Zip) file support for local reading."""
import os
import zipfile
import json
from PIL import Image
from core.config import COLORS

class CBZManager:
    """Manage local CBZ files and create CBZ from downloaded chapters."""

    @staticmethod
    def read_cbz(filepath):
        """Read a CBZ file and return list of image paths/data."""
        if not os.path.exists(filepath):
            return []

        pages = []
        with zipfile.ZipFile(filepath, 'r') as z:
            for name in sorted(z.namelist()):
                if name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                    pages.append({'name': name, 'data': z.read(name)})
        return pages

    @staticmethod
    def create_cbz(source_dir, output_path, metadata=None):
        """Create a CBZ file from a directory of images.

        Args:
            source_dir: Directory containing image files
            output_path: Output .cbz file path
            metadata: Optional dict with title, author, etc.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add metadata
            if metadata:
                zf.writestr('comicinfo.json', json.dumps(metadata, indent=2))

            # Add images
            valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            files = sorted([f for f in os.listdir(source_dir) 
                          if f.lower().endswith(valid_exts)])

            for f in files:
                zf.write(os.path.join(source_dir, f), f)

        return output_path

    @staticmethod
    def create_cbz_from_chapter(manga_id, chapter_id, chapter_dir, output_dir):
        """Create CBZ from a downloaded chapter directory."""
        metadata = {
            'manga_id': manga_id,
            'chapter_id': chapter_id,
            'type': 'manga_chapter',
        }

        output_path = os.path.join(output_dir, f"{manga_id}_{chapter_id}.cbz")
        return CBZManager.create_cbz(chapter_dir, output_path, metadata)

    @staticmethod
    def scan_cbz_directory(directory):
        """Scan directory for CBZ files."""
        cbz_files = []
        if not os.path.exists(directory):
            return cbz_files

        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.lower().endswith('.cbz'):
                    path = os.path.join(root, f)
                    try:
                        with zipfile.ZipFile(path, 'r') as z:
                            # Try to read metadata
                            meta = {}
                            try:
                                meta = json.loads(z.read('comicinfo.json'))
                            except:
                                pass

                            # Count images
                            img_count = len([n for n in z.namelist() 
                                           if n.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))])

                            cbz_files.append({
                                'id': path,
                                'title': meta.get('title', os.path.splitext(f)[0]),
                                'author': meta.get('author', 'Unknown'),
                                'path': path,
                                'pages': img_count,
                                'source': 'local_cbz',
                            })
                    except:
                        pass

        return cbz_files
