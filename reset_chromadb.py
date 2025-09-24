#!/usr/bin/env python
"""Reset ChromaDB by removing the existing database"""

import shutil
import os

chroma_path = "./chroma_db"

if os.path.exists(chroma_path):
    try:
        shutil.rmtree(chroma_path)
        print(f"Successfully removed {chroma_path}")
    except Exception as e:
        print(f"Error removing {chroma_path}: {e}")
        # Try to just rename it
        try:
            os.rename(chroma_path, f"{chroma_path}_old")
            print(f"Renamed {chroma_path} to {chroma_path}_old")
        except Exception as e2:
            print(f"Error renaming: {e2}")
else:
    print(f"{chroma_path} does not exist")