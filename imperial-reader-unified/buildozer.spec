[app]
title = Imperial Reader
package.name = imperialreader
package.domain = com.imperialreader
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json,xml,txt
version = 1.0
requirements = python3,kivy==2.3.0,kivymd==1.1.1,requests,urllib3,Pillow,beautifulsoup4,lxml,pysocks
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 28
android.ndk = 25.2.9519653
android.sdk = 34
android.arch = arm64-v8a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.wakelock = True
android.presplash_color = #0A0A0A

[buildozer]
log_level = 2
warn_on_root = 1
