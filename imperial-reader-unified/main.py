#!/usr/bin/env python3
"""
Imperial Reader - Unified Manga Reader
Supports Desktop (Linux/Mac/Windows) and Android
Black & Gold Theme | Offline Downloads | Library | Proxy | Extensions
"""
import sys
import os

# Platform detection
from kivy.utils import platform
IS_ANDROID = platform == 'android'
IS_DESKTOP = platform in ('linux', 'win', 'macosx')

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui.app import ImperialReaderApp

if __name__ == '__main__':
    ImperialReaderApp().run()
