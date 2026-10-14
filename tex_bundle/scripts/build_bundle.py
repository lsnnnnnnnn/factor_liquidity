"""Package report sources, aggregate data and rendered figures without build files."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
destination = root.parent / 'dist' / 'factor_liquidity_tex_bundle.zip'
destination.parent.mkdir(exist_ok=True)
with ZipFile(destination, 'w', compression=ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if path.is_file() and not any(p in {'build', '.venv', '.git', '__pycache__', '.DS_Store', '.cache'} for p in relative.parts):
            archive.write(path, Path('tex_bundle') / relative)
print(destination)
