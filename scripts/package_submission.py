"""
Clean submission packager for Visakhapatnam Transportation Platform.
Creates a portable, reproducible ZIP archive excluding node_modules,
virtualenvs, caches, and build artifacts.
"""

import os
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".turbo",
    "test-results"
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".log"
}

EXCLUDE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    ".env",
    ".env.local",
    "verify_production_numerics.py"
}

def create_package():
    output_filename = ROOT_DIR.parent / "Visakhapatnam_Transportation_Platform_SIH.zip"
    alt_filename = ROOT_DIR.parent / "Quantum project.zip"
    print(f"[PACKAGE] Target ZIP: {output_filename}")
    
    count = 0
    with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
            
            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                if any(file.endswith(ext) for ext in EXCLUDE_EXTENSIONS):
                    continue
                
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR)
                
                # Check that no parent is in exclude dirs
                if any(part in EXCLUDE_DIRS for part in rel_path.parts):
                    continue

                zipf.write(full_path, arcname=str(rel_path))
                count += 1

    # Also sync clean copy to Quantum project.zip
    import shutil
    shutil.copyfile(output_filename, alt_filename)

    size_mb = output_filename.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Packaged {count} files ({size_mb:.2f} MB) cleanly without node_modules or pycache!")
    print(f"          Synced to both {output_filename.name} and {alt_filename.name}")
    print(f"[VERIFY] Extract to any clean directory and run:")
    print("         pip install -r backend/requirements.txt")
    print("         cd frontend && npm ci && npm run build")
    return output_filename

if __name__ == "__main__":
    create_package()
