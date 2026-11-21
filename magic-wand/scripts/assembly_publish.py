"""Package the reviewed rod-holder assembly so GitHub Pages can serve it."""

from hashlib import sha256
from html import escape
import json
from pathlib import Path
import posixpath
import re
import subprocess

from paths import DOCS, REPOSITORY, ROOT


HARDWARE = ROOT / 'hardware'
PUBLIC = DOCS / 'assembly'
VIEWER = HARDWARE / 'carbon-rod-holders' / 'assembly'
GUIDE = HARDWARE / 'carbon-rod-holders-r57-pin-hinge' / 'exports' / 'assembly-guide.json'
# Pin the public runtime to the checked R57 release. Local viewer experiments stay local.
RUNTIME_REV = 'a907ae7ccc4f387898801f6f0f96df0c3acf1c34'
IMPORT = re.compile(r'''(\b(?:from|import)\s*)(['"])(\.\.?/[^'"\n]+)\2''')
ASSET = re.compile(r'''new URL\(\s*['"](\.\.?/[^'"\n]+\.stl)['"]\s*,\s*import\.meta\.url\)''')
HTML_REFERENCE = re.compile(r'''((?:href|src)=")([^"\n]+\.(?:css|mjs|svg))(")''')


def public_path(source: Path) -> Path:
    if source.is_relative_to(HARDWARE):
        return PUBLIC / 'assets' / source.relative_to(HARDWARE)
    if source.is_relative_to(DOCS / 'lib'):
        return source
    raise ValueError(f'Assembly asset is outside the public hardware or vendor roots: {source}')


def relative_url(origin: Path, target: Path) -> str:
    relative = posixpath.relpath(target, origin.parent)
    return relative if relative.startswith('.') else './' + relative


def runtime_source(path: Path) -> bytes:
    return subprocess.check_output(
        ['git', 'show', f'{RUNTIME_REV}:{path.relative_to(REPOSITORY).as_posix()}'], cwd=REPOSITORY,
    )


def artifacts() -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    entry = PUBLIC / 'index.html'

    def runtime_asset(source: Path) -> Path:
        dest = public_path(source)
        if dest in files:
            return dest
        if source.is_relative_to(DOCS / 'lib'):
            if not source.is_file():
                raise FileNotFoundError(source)
            return dest
        data = runtime_source(source)
        files[dest] = data
        if source.suffix == '.mjs':
            script = data.decode()

            def import_url(match: re.Match) -> str:
                name, _, query = match[3].partition('?')
                imported = runtime_asset((source.parent / name).resolve())
                suffix = '?' + query if query else ''
                return f'{match[1]}{match[2]}{relative_url(dest, imported)}{suffix}{match[2]}'

            for name in ASSET.findall(script):
                runtime_asset((source.parent / name).resolve())
            files[dest] = IMPORT.sub(import_url, script).encode()
        return dest

    def html_url(match: re.Match) -> str:
        target = runtime_asset((VIEWER / match[2]).resolve())
        return match[1] + relative_url(entry, target) + match[3]

    page = HTML_REFERENCE.sub(html_url, runtime_source(VIEWER / 'index.html').decode())
    manual = (GUIDE.parents[1] / 'README.md').read_text()
    heading = 'Click without moving the pointer'
    _, marker, instructions = manual.partition(f'\n## {heading}\n')
    paragraph = instructions.partition('\n## ')[0].strip()
    if not marker or not paragraph:
        raise ValueError('The public assembly guide is missing its OP1 click instructions')
    tip = f'<details><summary>{heading}</summary><p>{escape(paragraph)}</p></details>'
    page = page.replace('<p id="part-note"', tip + '\n<p id="part-note"', 1)
    files[entry] = page.encode()

    guide = json.loads(GUIDE.read_bytes())
    for name, digest in guide['sources']['meshes_sha256'].items():
        mesh = (GUIDE.parent / name).resolve()
        destination = public_path(mesh)
        data = mesh.read_bytes()
        if mesh.suffix != '.stl' or sha256(data).hexdigest() != digest:
            raise ValueError(f'Unexpected assembly mesh: {mesh.relative_to(REPOSITORY)}')
        files[destination] = data

    guide['defaultViews']['keys'] = 'pin_hinge'
    destination = public_path(GUIDE)
    files[destination] = (json.dumps(guide, separators=(',', ':'), allow_nan=False) + '\n').encode()
    catalog = public_path(VIEWER / 'catalog.json')
    version = dict(id='r57', label='R57 · Rod-mounted prototype', guide=relative_url(catalog, destination), groupKeys=True)
    files[catalog] = (json.dumps(dict(current='r57', versions=[version]), indent=2) + '\n').encode()
    return files
