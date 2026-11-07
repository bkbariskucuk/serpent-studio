#!/usr/bin/env python3
"""Install the official AppImage as a per-user Linux desktop application."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

REPO = 'bkbariskucuk/serpent-studio'


def fetch(url, target=None):
    request = urllib.request.Request(url, headers={'User-Agent': 'SerpentStudio-Installer'})
    with urllib.request.urlopen(request, timeout=120) as response:
        if target is None:
            return response.read()
        with open(target, 'wb') as output:
            shutil.copyfileobj(response, output)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def desktop_string(value):
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')


def exec_argument(path):
    value = str(path).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return desktop_string('"' + value + '"')


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.serpent-install-', dir=destination.parent)
    os.close(fd)
    try:
        shutil.copy2(source, name)
        os.replace(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def validate_bundle(extracted):
    assets = extracted / 'usr/bin/ui/assets'
    manifest = json.loads((assets / 'icons/manifest.json').read_text())
    assert sha256(assets / 'splash_logo.svg') == manifest['source_sha256'], 'Invalid icon source'
    for relative, expected in manifest['files'].items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or path.parts[0] != 'hicolor':
            raise ValueError('Invalid icon path')
        source = assets / 'icons' / path
        if sha256(source) != expected:
            raise ValueError('Invalid icon: ' + relative)
    return assets, manifest


def register(image, extracted, data):
    assets, manifest = validate_bundle(extracted)
    # Replace ALL old icon sizes, not just the desktop entry's preferred PNG.
    for relative in manifest['files']:
        atomic_copy(assets / 'icons' / relative, data / 'icons' / relative)
    icon = data / 'icons/hicolor/256x256/apps/serpentstudio.png'
    entry = data / 'applications/serpentstudio.desktop'
    if entry.exists():
        backup = data / 'serpent-studio/launcher-backups/before-appimage-install.desktop'
        if not backup.exists():
            atomic_copy(entry, backup)
    content = f'''[Desktop Entry]
Type=Application
Name=Serpent Studio
Comment=Serpent reactor modelling and analysis
Exec={exec_argument(image)} %F
Icon={desktop_string(icon)}
Terminal=false
StartupNotify=true
StartupWMClass=serpent-studio
Categories=Science;Physics;Engineering;
MimeType=text/x-serpent;text/plain;
Keywords=Serpent;Monte Carlo;Reactor;Nuclear;
X-SerpentStudio-Managed=true
Actions=SafeMode;

[Desktop Action SafeMode]
Name=Open without splash
Name[tr]=Açılış ekranı olmadan aç
Exec={exec_argument(image)} --no-splash %F
Icon={desktop_string(icon)}
'''
    entry.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='serpent-entry-') as temp:
        staged = Path(temp) / 'serpentstudio.desktop'
        staged.write_text(content)
        if shutil.which('desktop-file-validate'):
            subprocess.run(['desktop-file-validate', str(staged)], check=True)
        atomic_copy(staged, entry)
    entry.chmod(0o644)
    for command in (['update-desktop-database', str(entry.parent)],
                    ['gtk-update-icon-cache', '-f', '-t', str(data / 'icons/hicolor')],
                    ['kbuildsycoca6', '--noincremental'] if shutil.which('kbuildsycoca6') else
                    ['kbuildsycoca5', '--noincremental']):
        if shutil.which(command[0]):
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--appimage', type=Path, help='Use a downloaded official AppImage; hash is still verified online')
    parser.add_argument('--version', default='latest')
    args = parser.parse_args()
    if args.version != 'latest' and not re.fullmatch(r'v\d+\.\d+\.\d+\.\d+', args.version):
        parser.error('Invalid version')
    endpoint = 'latest' if args.version == 'latest' else 'tags/' + args.version
    release = json.loads(fetch(f'https://api.github.com/repos/{REPO}/releases/{endpoint}'))
    if release['draft'] or release['prerelease']:
        raise ValueError('Expected a published stable release')
    asset = next(a for a in release['assets'] if a['name'] == 'Serpent.Studio.AppImage')
    sums = next(a for a in release['assets'] if a['name'] == 'SHA256SUMS.txt')
    expected = None
    for line in fetch(sums['browser_download_url']).decode().splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1].lstrip('*') == asset['name']:
            expected = fields[0]
    if not expected or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Missing release checksum')
    if asset.get('digest') and asset['digest'] != 'sha256:' + expected:
        raise ValueError('Release checksums disagree')
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    if not data.is_absolute():
        raise ValueError('XDG_DATA_HOME must be absolute')
    image = data / 'serpent-studio/application/Serpent.Studio.AppImage'
    with tempfile.TemporaryDirectory(prefix='serpent-appimage-install-') as temp:
        temp = Path(temp)
        source = temp / asset['name']
        print('Preparing ' + release['tag_name'], flush=True)
        if args.appimage:
            shutil.copy2(args.appimage, source)
        else:
            fetch(asset['browser_download_url'], source)
        if source.stat().st_size != asset['size'] or sha256(source) != expected:
            raise ValueError('Downloaded AppImage checksum/size mismatch; installation unchanged')
        source.chmod(0o755)
        subprocess.run([str(source), '--appimage-extract'], cwd=temp, stdout=subprocess.DEVNULL, check=True)
        extracted = temp / 'squashfs-root'
        if (extracted / 'usr/bin/VERSION').read_text().strip() != release['tag_name']:
            raise ValueError('Embedded version mismatch')
        validate_bundle(extracted)
        atomic_copy(source, image)
        image.chmod(0o755)
        entry = register(image, extracted, data)
    print('Installed: ' + str(image))
    print('Application menu: Serpent Studio (' + str(entry) + ')')
    print('Projects and settings were preserved. Pin Serpent Studio from your application menu.')


if __name__ == '__main__':
    main()
