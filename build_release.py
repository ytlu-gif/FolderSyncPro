"""Build Windows executables; optionally compile an Inno Setup installer."""

import argparse
from pathlib import Path
import subprocess
import sys

from version import APP_VERSION, WINDOWS_VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer', type=Path, help='Path to Inno Setup ISCC.exe')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    slug = 'v' + APP_VERSION.replace('.', '_').replace('-', '_')
    work = root / ('build_' + slug)
    dist = root / ('dist_' + slug)
    work.mkdir(exist_ok=True)
    version_file = work / 'version_info.txt'
    version_file.write_text(
        'VSVersionInfo(\n'
        f' ffi=FixedFileInfo(filevers={WINDOWS_VERSION!r}, prodvers={WINDOWS_VERSION!r}, '
        'mask=0x3f, flags=0x2, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n'
        ' kids=[StringFileInfo([StringTable("040904B0", [\n'
        '  StringStruct("CompanyName", "FolderSyncPro"),\n'
        '  StringStruct("ProductName", "FolderSyncPro"),\n'
        f'  StringStruct("ProductVersion", "{APP_VERSION}"),\n'
        f'  StringStruct("FileVersion", "{APP_VERSION}")\n'
        ' ])]), VarFileInfo([VarStruct("Translation", [1033, 1200])])]\n)',
        encoding='utf-8',
    )
    for name, entry in [('FolderSyncPro', 'main.py'), ('FolderSyncProUsnHelper', 'usn_helper.py')]:
        command = [
            sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed',
            '--name', name, '--distpath', str(dist), '--workpath', str(work / name),
            '--specpath', str(work), '--version-file', str(version_file),
        ]
        if name == 'FolderSyncPro':
            command += [
                '--add-data', str(root / 'assets') + ';assets', '--icon', str(root / 'assets/icon.ico'),
                '--collect-all', 'ttkbootstrap', '--hidden-import', 'watchdog.observers',
                '--hidden-import', 'watchdog.events',
            ]
        subprocess.run(command + [str(root / entry)], cwd=root, check=True)
    if args.installer:
        subprocess.run([
            str(args.installer.resolve()),
            f'/DMyAppVersion={APP_VERSION}',
            '/DMyAppVersionInfo=' + '.'.join(map(str, WINDOWS_VERSION)),
            '/DBuildDist=' + dist.name,
            str(root / 'installer.iss'),
        ], cwd=root, check=True)
    print(f'Built FolderSyncPro {APP_VERSION}: {dist}')


if __name__ == '__main__':
    main()
