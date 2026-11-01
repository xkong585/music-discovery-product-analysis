"""Download the original author release; never generate replacement events."""
from pathlib import Path
import urllib.request,hashlib,shutil
p=Path(__file__).resolve().parents[1]/'data/raw/lastfm-dataset-1K.tar.gz';p.parent.mkdir(parents=True,exist_ok=True)
if not p.exists():
 with urllib.request.urlopen('https://zenodo.org/records/6090214/files/lastfm-dataset-1K.tar.gz?download=1',timeout=120) as r,p.open('wb') as f:shutil.copyfileobj(r,f)
h=hashlib.md5()
with p.open('rb') as f:
 while b:=f.read(8*1024*1024):h.update(b)
assert h.hexdigest()=='a79a6808f54f73354789a9fb02cb1e41','Partial or changed source; remove file and download again.'
print(p)
