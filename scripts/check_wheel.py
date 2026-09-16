"""Check that the offline template ships and the wheel has no runtime deps."""
from pathlib import Path
from zipfile import ZipFile

wheel = next(Path("dist").glob("*.whl"))
with ZipFile(wheel) as archive:
    assert "profile_analyzer/profiler_explorer.html" in archive.namelist()
    metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
    metadata = archive.read(metadata_name).decode()
    assert "Requires-Dist:" not in metadata
print(f"Verified bundled template and zero runtime dependencies: {wheel.name}")
