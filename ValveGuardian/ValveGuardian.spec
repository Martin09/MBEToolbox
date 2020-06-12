# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['ValveGuardian.py'],
             pathex=['.'],
             binaries=[( '../MBE_Tools.py', '.' ),
                       ( '../recipe_helper.py', '.' ),
                       ( '../mbe_calibration.py', '.' )],
             datas=[],
             hiddenimports=['matplotlib',
                            'pandas'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          Tree('..\\Virtual_MBE', prefix='Virtual_MBE\\'),
          a.zipfiles,
          a.datas,
          [],
          name='ValveGuardian',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
