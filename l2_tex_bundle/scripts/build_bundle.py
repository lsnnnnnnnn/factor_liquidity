"""Package the editable report and public derived data; leave build files out."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
destination = root.parent / "dist" / "factor_liquidity_l2_tex_bundle.zip"
destination.parent.mkdir(exist_ok=True)
with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not set(relative.parts) & {"build", ".venv", ".git", "__pycache__", ".DS_Store", ".cache"}:
            archive.write(path, Path("l2_tex_bundle") / relative)
print(destination)
