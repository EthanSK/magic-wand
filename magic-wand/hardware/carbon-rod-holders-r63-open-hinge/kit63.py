"""Print the replacement parts for the broken R62 kit on their separate PETG bases."""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / "exports"
R62 = HERE.parent / "carbon-rod-holders-r62-compact-guard"
sys.path.insert(0, str(R62))
import kit62
import design63

plate = kit62.plate61
PRINT_POSES = {"Key_Carrier": (-90, 0), "Touch_Paddle": (180, 90),
               "Socket_Backer_Left": (0, 0), "Rod_Collet": (-90, 0)}


def parts():
    rows = []
    for previous in kit62.parts():
        name = previous["name"]
        if name in PRINT_POSES:
            source = OUT / previous["source"].name
            pose = plate.printer.pose_for(source, *PRINT_POSES[name])
            row=dict(previous, source=source, assembly_to_print=pose)
            if name == "Key_Carrier":
                # The old underside fin at -13.5 crossed the new battery entrance.
                # Root its replacement on the inboard lip; reserve the open mouth.
                panel=row["panel"]
                ties=[dict(t, at=-11.0) if t["face"]=="-y" and t["at"]==-13.5 else t
                      for t in panel["ties"]]
                xb=design63.PACK_X
                zb=design63.PACK_Z
                keep=[*panel["keep_clear"],[design63.LEAF_X[0]-.45,zb[0]-.15,xb[1]+.15,zb[1]+.14]]
                row["panel"]=dict(panel,ties=ties,keep_clear=keep,fin_thickness=1.70)
            if name == "Socket_Backer_Left":
                row["panel"] = dict(row["panel"], size=(32,20))
            if name == "Touch_Paddle":
                # The rear-centre tab entered the seated pin clip by 0.072 mm³.
                # Attach the second tab to the side, clear of the well.
                row["panel"] = dict(row["panel"], ties=[(-1,0),(0,1)])
            rows.append(row)
    source = OUT / design63.COLLET_FILE
    rows.append(dict(name="Rod_Collet", source=source, mesh_reference=source.name,
                     assembly_to_print=plate.printer.pose_for(source,*PRINT_POSES["Rod_Collet"]),
                     bed_center=(97.5,35), panel=dict(size=(19,19), ties=[(1,0)], tie_width=1.6)))
    assert {row["name"] for row in rows} == PRINT_POSES.keys()
    return rows


def panel_builder(body, options):
    backed = plate.printer.panel_builder(body, options)
    if options.get("wire_exit"):
        pose = plate.printer.pose_for(OUT / "Touch_Paddle-assembly.stl", *PRINT_POSES["Touch_Paddle"])
        clearance = plate.lead().transform(pose[:3]).project().offset(.65).extrude(1).translate((0, 0, -.2))
        backed -= clearance - body
    return backed


def layout(path):
    plate.printer.write_layout(parts(), path, plate.plate60.prior.p58.TOWER,
                               "R63 replacement key holder, paddle, backing strip and rod grip", panel_builder=panel_builder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    layout(parser.parse_args().file)
