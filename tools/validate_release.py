"""Check a source tree or ZIP offline: layout, hashes, syntax, links and exclusions.

Does not execute notebooks, install dependencies or contact Databricks. Exit status
is nonzero on any finding. Archive checks never extract or execute archive members.
"""
import argparse
import ast
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path, PurePosixPath

REQUIRED = {
    'README.md', '.gitignore', 'requirements-analysis.txt', 'docs/setup.md',
    'docs/code_guide.md', 'docs/release_notes.md', 'resources/jobs/incremental_job.json',
    'resources/pipelines/README.md', 'src/transformations/bronze/01_bronze_ingesta.ipynb',
    'src/transformations/silver/02_silver_preparacion.ipynb',
    'src/transformations/gold/03_gold_metricas.ipynb',
    'src/quality/00_auditoria_modelo.ipynb',
}
PRIVATE_PARTS = {'.deployment', '__pycache__', '.venv', '.git', 'output', 'data'}
PRIVATE_NAMES = {'.env', '.databrickscfg', 'cases.json', 'pilot.json', 'receipts.html',
                 'review.html', 'private_scored_sample.json', 'review_events.jsonl'}
SECRET = re.compile(rb'dapi[a-f0-9]{32}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}')


def validate(files, archive=False):
    """Return actionable findings without printing file contents or secret matches."""
    errors = [f'Missing required file: {name}' for name in sorted(REQUIRED - files.keys())]
    for name, data in files.items():
        parts = PurePosixPath(name).parts
        if PurePosixPath(name).is_absolute() or '..' in parts or '\\' in name:
            errors.append(f'Unsafe member path: {name}')
        if PRIVATE_PARTS.intersection(parts) or PurePosixPath(name).name in PRIVATE_NAMES:
            errors.append(f'Private/runtime file: {name}')
        if SECRET.search(data):
            errors.append(f'Credential-pattern match requires review: {name}')
        try:
            if name.endswith('.py'):
                ast.parse(data, filename=name)
            elif name.endswith(('.json', '.ipynb')):
                obj = json.loads(data)
                if name.endswith('.ipynb'):
                    for i, cell in enumerate(obj['cells']):
                        if cell['cell_type'] == 'code':
                            if cell.get('outputs'):
                                errors.append(f'Notebook output must be cleared: {name}:{i}')
                            source = ''.join(cell['source'])
                            # Databricks notebook commands may use cell magics.
                            if not source.lstrip().startswith('%'):
                                ast.parse(source, filename=f'{name}:cell{i}')
            elif name.endswith('.md'):
                for link in re.findall(r'\]\(([^)]+)\)', data.decode('utf-8')):
                    if '://' in link or link.startswith(('#', 'mailto:')):
                        continue
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), link.split('#')[0]))
                    if target not in files and not any(p.startswith(target.rstrip('/') + '/') for p in files):
                        errors.append(f'Broken local link: {name} -> {link}')
        except (SyntaxError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'Invalid source/document: {name}: {type(exc).__name__}')
    if archive:
        try:
            manifest = json.loads(files['SHA256.json'])
            actual = {n for n in files if n != 'SHA256.json'}
            if set(manifest) != actual:
                errors.append('Manifest does not cover exactly the archive files')
            for name in sorted(actual & manifest.keys()):
                if hashlib.sha256(files[name]).hexdigest() != manifest[name]:
                    errors.append(f'Hash mismatch: {name}')
        except (KeyError, ValueError, TypeError):
            errors.append('Missing or invalid SHA256.json')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Validate a ZIP instead of the local release tree')
    args = parser.parse_args()
    errors = []
    if args.archive:
        with zipfile.ZipFile(args.archive) as archive:
            members = [i for i in archive.infolist() if not i.is_dir()]
            if len({i.filename for i in members}) != len(members):
                errors.append('Duplicate archive member names')
            if any(not i.filename.startswith('Applebees_Fase2/') for i in members):
                errors.append('Unexpected archive root')
            if any((i.external_attr >> 16) & 0o170000 == 0o120000 for i in members):
                errors.append('Archive contains a symbolic link')
            if sum(i.file_size for i in members) > 50_000_000:
                raise SystemExit('Archive exceeds expected source-release size')
            files = {i.filename.removeprefix('Applebees_Fase2/'): archive.read(i) for i in members}
    else:
        root = Path(__file__).resolve().parents[1]
        roots = {'resources', 'src', 'configs', 'tests', 'tools', 'docs', 'evidence', 'notebooks'}
        files = {}
        for path in root.rglob('*'):
            rel = path.relative_to(root)
            if PRIVATE_PARTS.intersection(rel.parts) or not path.is_file():
                continue
            if rel.parts[0] in roots or rel.as_posix() in {'README.md', '.gitignore', 'requirements-analysis.txt'}:
                if path.is_symlink():
                    errors.append(f'Symbolic link not allowed: {rel}')
                files[rel.as_posix()] = path.read_bytes()
    errors.extend(validate(files, archive=bool(args.archive)))
    print(json.dumps({'status': 'FAIL' if errors else 'PASS', 'files': len(files),
                      'mode': 'archive' if args.archive else 'source', 'findings': errors}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
