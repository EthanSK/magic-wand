"""Point the permanent holder viewer at a regenerated current CAD revision.

Called by the revision's build_preview.py, so geometry and the pointer update
together. Rebuilding an older archive cannot replace a newer current revision.
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent

def publish(revision: Path, destination: Path = HERE) -> None:
    def number(name: str) -> int:
        match = re.fullmatch(r'carbon-rod-holders-r(\d+)-[a-z0-9-]+', name)
        if not match:
            raise ValueError('Invalid holder revision')
        return int(match[1])

    target = destination / 'current.json'
    current = json.loads(target.read_text()) if target.exists() else None
    if current and number(current['revision']) > number(revision.name):
        return
    scene = revision / 'exports/review-scene.json'
    # Require a complete scene before moving the one current-model pointer.
    data = json.loads(scene.read_text())
    assert data['parameters']['revision'] == revision.name
    record = {'revision': revision.name,
              'scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest()}
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.replace(target)
