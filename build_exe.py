"""
Build script to create a standalone Windows executable for RazaiColor.
Requires: pip install pyinstaller

Usage:
    python build_exe.py
"""
import os
import subprocess
import sys
import site
import shutil


def find_streamlit_path():
    """Locate the streamlit package directory."""
    import streamlit
    return os.path.dirname(streamlit.__file__)


def find_package_path(package_name):
    """Locate a package directory in site-packages."""
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        candidate = os.path.join(sp, package_name)
        if os.path.isdir(candidate):
            return candidate
    return None


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(project_root, "dist")
    build_dir = os.path.join(project_root, "build")

    streamlit_path = find_streamlit_path()
    print(f"Streamlit found at: {streamlit_path}")

    # Collect hidden imports needed by the app
    hidden_imports = [
        "streamlit",
        "streamlit.runtime",
        "streamlit.runtime.scriptrunner",
        "streamlit.web.bootstrap",
        "streamlit.web.server",
        "PIL",
        "numpy",
        "skimage",
        "skimage.color",
        "skimage.exposure",
        "skimage.filters",
        "scipy",
        "src",
        "src.recolor",
        "src.recolor.color_spaces",
        "src.recolor.gamut",
        "src.recolor.luminance",
        "src.recolor.masks",
        "src.recolor.models",
        "src.recolor.pipeline",
        "src.recolor.texture",
    ]

    hidden_imports_args = []
    for mod in hidden_imports:
        hidden_imports_args.extend(["--hidden-import", mod])

    # Data files to include
    data_args = [
        "--add-data", f"{streamlit_path};streamlit",
        "--add-data", f"{os.path.join(project_root, 'app.py')};.",
        "--add-data", f"{os.path.join(project_root, 'src')};src",
    ]

    # Include assets if non-empty
    assets_dir = os.path.join(project_root, "assets")
    if os.path.isdir(assets_dir) and os.listdir(assets_dir):
        data_args.extend(["--add-data", f"{assets_dir};assets"])

    # Include .streamlit config if it exists
    streamlit_config = os.path.join(project_root, ".streamlit")
    if os.path.isdir(streamlit_config):
        data_args.extend(["--add-data", f"{streamlit_config};.streamlit"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "RazaiColor",
        "--onedir",
        "--console",       # keep console to see logs; change to --windowed to hide
        "--noconfirm",
        "--clean",
        *hidden_imports_args,
        *data_args,
        "--collect-all", "streamlit",
        "--collect-all", "skimage",
        "--copy-metadata", "streamlit",
        os.path.join(project_root, "run_app.py"),
    ]

    print("Running PyInstaller...")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode != 0:
        print("\n[FAIL] Build failed. Check the errors above.")
        sys.exit(1)

    # Copy app.py and src/ into the dist folder (redundancy for runtime)
    output_dir = os.path.join(dist_dir, "RazaiColor")
    for item in ["app.py"]:
        src = os.path.join(project_root, item)
        dst = os.path.join(output_dir, item)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            print(f"Copied {item}")

    src_dir_src = os.path.join(project_root, "src")
    src_dir_dst = os.path.join(output_dir, "src")
    if os.path.isdir(src_dir_dst):
        shutil.rmtree(src_dir_dst)
    shutil.copytree(src_dir_src, src_dir_dst)
    print("Copied src/")

    print(f"\n[OK] Build complete!")
    print(f"  Output: {output_dir}")
    print(f"  Executable: {os.path.join(output_dir, 'RazaiColor.exe')}")
    print(f"\nTo distribute, zip the entire '{output_dir}' folder.")


if __name__ == "__main__":
    main()
