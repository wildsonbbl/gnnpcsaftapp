from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("kivy_matplotlib_widget")
