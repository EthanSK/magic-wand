"""Print-layer screening: unsupported starts and thin sections per 0.2 mm layer."""
import sys, json
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import holder38 as d
import manifold3d as mf
import numpy as np
R = mf.JoinType.Round

def screen(name, solid, to_print, height, report_thin=.6):
    """to_print maps assembly -> print frame (print Z up)."""
    p = solid.transform(to_print)
    z0 = p.bounding_box()[2]
    prev = None
    rows = []
    for k in range(int(round(height / .2))):
        z = z0 + .2 * k + .1
        sec = p.slice(z)
        if prev is not None:
            reach = prev.offset(.45, R, 2., 16)          # one bead of overhang allowance
            for piece in sec.decompose():
                new = piece - reach
                if piece.area() > .02 and (piece ^ reach).area() < .02:
                    b = piece.bounds()
                    rows.append({"layer": k + 1, "z": round(z - z0, 2), "kind": "unsupported island", "area": round(piece.area(), 3),
                                 "bounds": [round(v, 2) for v in b]})
                elif new.area() > 1.2:
                    for q in new.decompose():
                        if q.area() > 1.2:
                            rows.append({"layer": k + 1, "z": round(z - z0, 2), "kind": "overhang beyond one bead", "area": round(q.area(), 3),
                                         "bounds": [round(v, 2) for v in q.bounds()]})
        thin = sec - sec.offset(-.2, R, 2., 16).offset(.2, R, 2., 16)
        for q in thin.decompose():
            if q.area() > report_thin:
                rows.append({"layer": k + 1, "z": round(z - z0, 2), "kind": "section thinner than 0.4", "area": round(q.area(), 3),
                             "bounds": [round(v, 2) for v in q.bounds()]})
        if k == 0:
            print(name, "first layer pieces", len(sec.decompose()), "area", round(sec.area(), 2),
                  [(round(q.area(), 2), [round(v, 1) for v in q.bounds()]) for q in sec.decompose()])
        prev = sec
    return rows


from pathlib import Path
import hashlib
car = d.carrier(); br = d.bracket()
report = {"source_sha256": hashlib.sha256(Path(d.__file__).read_bytes()).hexdigest(),
          "not_slicer_toolpaths": True,
          "assumption": "0.2 mm sections with 0.45 mm preceding-layer reach", "parts": {}}
for name,solid,matrix,height in (("carrier",car,((1,0,0,0),(0,0,1,0),(0,-1,0,0)),41.85),
                                ("bracket",br,((1,0,0,0),(0,0,-1,0),(0,1,0,0)),40.24)):
    rows=screen(name,solid,matrix,height)
    report["parts"][name]={"orientation": "rear face down" if name=="carrier" else "front face down",
                            "warnings":rows}
(ROOT / "evidence" / "layer-screen.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({name:{"warning_count":len(p["warnings"]),"unsupported_starts":[r for r in p["warnings"] if r["kind"]=="unsupported island"]} for name,p in report["parts"].items()},indent=2))
