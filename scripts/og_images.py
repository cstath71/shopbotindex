#!/usr/bin/env python3
"""Render the social share cards assets/og.png and assets/og-store.png (1200x630)
from assets/og.html and assets/og-store.html with headless Chrome.
The robot logo comes from assets/brand/logo-hd.png (631 px source).
build.py copies the PNGs into dist/. Usage: python3 scripts/og_images.py"""
import os, shutil, subprocess, sys, tempfile
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A=os.path.join(ROOT,'assets')
CHROME=shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chromium-browser')
if not CHROME: sys.exit('Chrome/Chromium not found')
for name in ('og','og-store'):
    src=os.path.join(A,name+'.html'); out=os.path.join(A,name+'.png')
    with tempfile.TemporaryDirectory() as prof:
        subprocess.run([CHROME,'--headless=new','--disable-gpu','--no-sandbox','--hide-scrollbars',
            f'--user-data-dir={prof}','--force-device-scale-factor=1','--window-size=1200,630',
            '--default-background-color=0f172aff','--virtual-time-budget=3000',
            f'--screenshot={out}','file://'+src],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('wrote',out)
