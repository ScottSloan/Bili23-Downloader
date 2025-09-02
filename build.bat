@echo off

nuitka --standalone --nofollow-import-to=numpy,PIL --windows-console-mode=disable --file-version=1.66.0.0 --product-version=1.66.0.0 --windows-icon-from-ico=icon.ico --product-name="Bili23 Downloader" --company-name="Scott Sloan" --file-description="Bili23 Downloader" --copyright="Copyright (C) 2022-2025 Scott Sloan" --show-progress --mingw64 --output-dir=build GUI.py

pause