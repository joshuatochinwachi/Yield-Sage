import shutil, pathlib, os

src = pathlib.Path(os.environ.get("APPDATA", "")).parent / ".gemini" / "antigravity-ide" / "brain" / "b090b317-63b9-49cd-881c-66bf9ee9036e" / "yieldsage_readme_banner_1780479029960.png"
dst = pathlib.Path(__file__).parent / "frontend" / "public" / "readme_banner.png"

if src.exists():
    shutil.copy2(src, dst)
    print(f"✅ Banner copied to {dst}")
else:
    # Try alternate path
    home = pathlib.Path.home()
    src2 = home / ".gemini" / "antigravity-ide" / "brain" / "b090b317-63b9-49cd-881c-66bf9ee9036e" / "yieldsage_readme_banner_1780479029960.png"
    if src2.exists():
        shutil.copy2(src2, dst)
        print(f"✅ Banner copied to {dst}")
    else:
        print(f"❌ Source not found. Expected: {src2}")
        print("Please manually copy the banner PNG into frontend/public/readme_banner.png")
