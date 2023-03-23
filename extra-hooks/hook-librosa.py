from PyInstaller.utils.hooks import collect_data_files
datas = collect_data_files("librosa")
datas+= collect_data_files("librosa.core")
datas+= collect_data_files("librosa.feature")
datas+= collect_data_files("librosa.util")