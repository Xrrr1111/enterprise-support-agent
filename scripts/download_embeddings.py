"""Fetch pinned open-source embeddings to an explicitly chosen external directory."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

REVISION = '2c4055b12046f11709e9df2c122e59ffbdc2f900'
REPOSITORY = 'Xenova/paraphrase-multilingual-MiniLM-L12-v2'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    target = parser.parse_args().directory.resolve()
    if target.drive.lower() == 'c:':
        raise ValueError('Choose a non-C drive for model storage')
    target.mkdir(parents=True, exist_ok=True)
    records = []
    for name in ['tokenizer.json', 'onnx/model_quantized.onnx']:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            partial = path.with_suffix('.partial')
            with urlopen(f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}', timeout=120) as response, partial.open('wb') as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            partial.replace(path)
        records.append({'file': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
        print(name, path.stat().st_size, flush=True)
    (target / 'provenance.json').write_text(json.dumps({'repository': REPOSITORY, 'revision': REVISION, 'files': records}, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
