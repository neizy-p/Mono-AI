[app]
title = Mono AI
package.name = monoai
package.domain = org.mono
source.dir = .
source.include_exts = py,png,jpg,ttf
version = 0.1
icon.filename = %(source.dir)s/icon.png
icon.adaptive_foreground.filename = %(source.dir)s/icon_fg.png
icon.adaptive_background.filename = %(source.dir)s/icon_bg.png
requirements = python3,kivy==2.3.0,requests,urllib3,chardet,idna,certifi,plyer,pyjnius,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_AUDIO
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
