import os.path
import glob
from PyInstaller.compat import EXTENSION_SUFFIXES
from PyInstaller.utils.hooks import collect_data_files, get_module_file_attribute


datas = collect_data_files("librosa")
librosa_dir = os.path.dirname(get_module_file_attribute("librosa"))
for ext in EXTENSION_SUFFIXES:
    ffimods = glob.glob(os.path.join(librosa_dir, "_lib", f"*_cffi_*{ext}*"))
    dest_dir = os.path.join("librosa", "_lib")
    for f in ffimods:
        binaries.append((f, dest_dir))