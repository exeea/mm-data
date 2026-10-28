"""Build the installable legacy add-on ZIP without requiring Blender."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
target = HERE / 'mm_materials.zip'
with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
    for path in sorted((HERE / 'mm_materials').glob('*.py')):
        archive.write(path, 'mm_materials/' + path.name)
    archive.write(HERE / 'README.md', 'mm_materials/README.md')
print(target)
