# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# 资源文件列表
datas = [
    ('chat.html', '.'),
    ('Dify后端接口调用指南.md', '.'),
]

# 隐藏导入（wxPython 常用）
hiddenimports = [
    'wx',
    'wx.html2',
    'urllib.request',
    'urllib.error',
    'http.server',
    'socket',
    'threading',
    'json',
    'subprocess',
    'base64',
    'tempfile',
    'uuid',
    'platform',
    'io',
]

a = Analysis(
    ['form_helper.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FormHelper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if sys.platform == 'win32' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FormHelper',
)

if sys.platform == 'darwin':
    # macOS 打包成 .app
    import os
    icon_path = 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None

    app = BUNDLE(
        coll,
        name='FormHelper.app',
        icon=icon_path,
        bundle_identifier='com.formhelper.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'NSRequiresAquaSystemAppearance': 'False',
            'CFBundleShortVersionString': '0.1.0',
            'CFBundleVersion': '0.1.0',
            'NSAppleScriptEnabled': 'False',
            # 屏幕录制权限说明
            'NSScreenCaptureDescription': '需要屏幕录制权限以截取右侧表单页面，用于AI智能分析填写建议。',
        },
    )
