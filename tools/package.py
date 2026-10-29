"""Build a portable archive of reviewed source/docs/evidence, never deployment state."""
import argparse,hashlib,json,zipfile
from validate_release import validate
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1]
allowed={'configs','resources','src','tools','tests','docs','evidence','notebooks'}
files=sorted(f for f in root.rglob('*') if f.is_file() and (f.relative_to(root).parts[0] in allowed or f.name in ['README.md','.gitignore','requirements-analysis.txt']) and not any(x in ['__pycache__','.deployment','build','.git','.venv'] for x in f.relative_to(root).parts) and f.suffix not in ['.pyc','.zip'])
paths={f.relative_to(root).as_posix() for f in files}
# Preserve the Sun Holdings repository layout, independently of workspace navigation.
required={
 'resources/jobs/incremental_job.json',
 'resources/pipelines/README.md',
 'src/transformations/bronze/01_bronze_ingesta.ipynb',
 'src/transformations/silver/02_silver_preparacion.ipynb',
 'src/transformations/gold/03_gold_metricas.ipynb',
 'README.md',
 'requirements-analysis.txt',
 'docs/setup.md',
 'docs/code_guide.md',
 'tools/validate_release.py',
}
if missing:=required-paths:
 raise ValueError(f'Missing repository layout files: {sorted(missing)}')
if any(f.is_symlink() for f in files):
 raise ValueError('Symbolic links are not allowed in a source release')
if findings:=validate({f.relative_to(root).as_posix():f.read_bytes() for f in files}):
 raise ValueError('Release validation failed: '+repr(findings))
for f in files:
 assert f.stat().st_size<2_000_000,f
 assert f.suffix in ['.md','.py','.json','.ipynb','.sql','.png'] or f.name in {'.gitignore','requirements-analysis.txt'},f
manifest={f.relative_to(root).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
a.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,'Applebees_Fase2/'+f.relative_to(root).as_posix())
 z.writestr('Applebees_Fase2/SHA256.json',json.dumps(manifest,indent=2))
print(json.dumps({'archive':str(a.output.resolve()),'files':len(files),'bytes':a.output.stat().st_size}))
