"""R54 sacrificial bed base for the rear-down key holder: a close panel joined by six braced fins.

The R53 holder stood on 441 mm2 of its own first layer, in a strip about 5 mm deep under a
51.5 mm tall part. Its wide panel was joined by two tabs, 3.1 mm wide and one layer thick
(1.2 mm2 in total). The panel stayed on the sheet and the holder left it.

Here the panel follows the real low outline of the holder across an open moat. Six fins cross
the moat. Each fin is thin across and tall, so it resists the holder rocking and still takes
one nip of flush cutters. Behind each fin a sloping buttress and a thick foot carry the load
into the panel. Nothing else touches the holder.

Coordinates are the bed-oriented frame used by the R53 plate before the part is moved to its
bed position: print X = assembly X, print Y = assembly Z, bed at Z = 0, rod axis at the origin.

panel keys
    size            (width, depth) of the panel rectangle, required
    centre          panel centre; default is the middle of the body's XY bounds, as in R53
    origin          rod axis in XY, default (0, 0); every station below is measured from it
    thickness       panel thickness, default 0.40 (two layers)
    layer           layer height used for the low sections, default 0.20
    moat            open gap between the holder and every sacrificial part, default 1.5
    fin_thickness   default 1.68 (four 0.42 mm lines)
    reach           buttress length beyond the moat, default 9.0
    foot            (half width, thickness) of the thick foot under each buttress, default (4.5, 1.2)
    ties            list of stations replacing TIES
    keep_clear      extra XY boxes (x0, y0, x1, y1) from the origin that stay free of base material
"""
import manifold3d as mf
import numpy as np

# Stations from the measured R53 sections. `face` is the direction the fin leaves the holder.
# +y  rear rim, top face (assembly top). Behind the upper caps: their travel starts at print Z 2.6
#     and 0.85 above this face, so a trimmed stub stays below it.
# -y  rear rim, underside. X 14.2 lies between the OP1 lead (X 4.5 to 11.5) and the upper-right
#     socket (X 16.7 outward, from print Z 3.0).
# +x / -x  outer faces of the hinge yoke, below the 2.6 mm level where the upper caps begin.
TIES = (
    dict(face="+y", at=21.5, height=3.4), dict(face="+y", at=-21.5, height=3.4),
    dict(face="-y", at=14.2, height=3.0), dict(face="-y", at=-14.2, height=3.0),
    dict(face="+x", at=16.2, height=2.4), dict(face="-x", at=16.2, height=2.4),
)
OVERLAP = 0.6      # how far each fin runs into the holder wall
YOKE_HALF = 12.8   # the hinge yoke and cap channel lie inside |X| < 11.5
YOKE_BAND = 2.6    # kept clear below and above the yoke top (cap seat, both nail reliefs)
WIRE_LANE = (3.9, -2.5, 12.0, 7.3)   # x0, y0, x1, y1 of the OP1 lead under the rim; no fin may root here
ROD_CLEAR = 5.2    # outer radius of the sprung rod ring; its bore and mouth stay open


def _box(x0, y0, x1, y1):
    return mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))


def _solid(section, z0, z1):
    return mf.Manifold.extrude(section, z1 - z0).translate((0, 0, z0))


def _filled(section):
    """Outer outlines only, so the rod bore and the yoke arch never receive an island."""
    outer = []
    for poly in section.to_polygons():
        p = np.asarray(poly)
        if 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]) > 0:
            outer.append(p)
    return mf.CrossSection(outer, mf.FillRule.NonZero) if outer else mf.CrossSection()


def _sections(body, top, layer):
    return [(z, body.slice(float(z))) for z in np.arange(layer / 2, top, layer)]


def _frame(face):
    """Outward unit vector and the tangent along the holder face."""
    out = dict(zip(("+x", "-x", "+y", "-y"), ((1, 0), (-1, 0), (0, 1), (0, -1))))[face]
    out = np.array(out, float)
    return out, np.array([-out[1], out[0]])


def _root(sections, tie, origin, thickness, layer):
    """Find the real face under one fin, layer by layer.

    Returns the innermost and outermost face position along the outward direction and the height
    the face really reaches. A fin never rises past the last layer where the holder is present.
    """
    out, tangent = _frame(tie["face"])
    # `at` is the X station for +/-y fins and the Y station for +/-x fins.
    if tie["face"][1] == "x":
        along = origin[1] + tie["at"]
        strip = _box(-500, along - thickness / 2 - 0.3, 500, along + thickness / 2 + 0.3)
    else:
        along = origin[0] + tie["at"]
        strip = _box(along - thickness / 2 - 0.3, -500, along + thickness / 2 + 0.3, 500)
    faces, height = [], 0.0
    for z, section in sections:
        if z > tie["height"]:
            break
        here = section ^ strip
        if here.is_empty():
            break
        points = np.concatenate(here.to_polygons())
        faces.append(float((points @ out).max()))
        height = z + layer / 2
    if height < 4 * layer:
        raise ValueError(f"No holder face for the fin at {tie}")
    centre = along * np.abs(tangent)  # the station coordinate on the tangent axis
    return dict(out=out, tangent=tangent, station=centre, inner=min(faces), outer=max(faces), height=height)


def _oriented(root, a0, a1, half):
    """Rectangle from a0 to a1 along the outward direction, `half` wide each side of the station."""
    o, t, c = root["out"], np.abs(root["tangent"]), root["station"]
    corners = [o * a0 + c - t * half, o * a1 + c - t * half, o * a1 + c + t * half, o * a0 + c + t * half]
    section = mf.CrossSection([np.array(corners)])
    return section if section.area() > 0 else mf.CrossSection([np.array(corners[::-1])])


def _buttress(root, start, reach, half, height, low):
    """Rib that falls from the fin height to the foot over `reach`, built as stepped layers."""
    steps = max(2, int(round((height - low) / 0.2)))
    parts = []
    for i in range(steps):
        z0 = low + (height - low) * i / steps
        z1 = low + (height - low) * (i + 1) / steps
        run = reach * (1 - i / steps)
        parts.append(_solid(_oriented(root, start - 0.01, start + run, half), z0 - 0.001, z1))
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def layout54(body, panel):
    """All plan shapes and fin data. `backed_panel54` and `report54` both build on this."""
    layer = panel.get("layer", 0.20)
    moat = panel.get("moat", 1.5)
    thickness = panel.get("thickness", 0.40)
    fin = panel.get("fin_thickness", 1.68)
    reach = panel.get("reach", 9.0)
    foot_half, foot_top = panel.get("foot", (4.5, 1.2))
    origin = np.array(panel.get("origin", (0.0, 0.0)), float)
    ties = [dict(t) for t in panel.get("ties", TIES)]
    bounds = body.bounding_box()
    if abs(bounds[2]) > 0.015:
        raise ValueError("The body must already sit on the bed")
    top = max(t["height"] for t in ties)
    sections = _sections(body, top + layer, layer)
    # Everything the holder occupies up to the tallest brace, with its holes closed.
    shadow = _filled(mf.CrossSection.batch_boolean([s for _, s in sections], mf.OpType.Add))
    guard = shadow.offset(moat, mf.JoinType.Round, 2.0, 32)
    bed = sections[0][1]
    yoke_top = float(np.concatenate((bed ^ _box(origin[0] - 11.5, -500, origin[0] + 11.5, 500)).to_polygons())[:, 1].max())
    clear = [
        # Hinge cap seat, cap channel mouth and both nail reliefs.
        _box(origin[0] - YOKE_HALF, yoke_top - YOKE_BAND, origin[0] + YOKE_HALF, yoke_top + YOKE_BAND),
        # Rod bore, the ring round it and the ring mouth.
        mf.CrossSection.circle(ROD_CLEAR + moat, 64).translate(tuple(origin)),
    ] + [_box(origin[0] + x0, origin[1] + y0, origin[0] + x1, origin[1] + y1) for x0, y0, x1, y1 in panel.get("keep_clear", ())]
    clear = mf.CrossSection.batch_boolean(clear, mf.OpType.Add)
    centre = np.array(panel.get("centre", ((bounds[0] + bounds[3]) / 2, (bounds[1] + bounds[4]) / 2)), float)
    w, h = panel["size"]
    outline = _box(centre[0] - w / 2, centre[1] - h / 2, centre[0] + w / 2, centre[1] + h / 2)
    outline = outline.offset(-1.3).offset(1.3, mf.JoinType.Round, 2.0, 24)
    keep_out = guard + (clear - shadow)
    sheet = outline - keep_out
    pieces = sorted(sheet.decompose(), key=lambda s: -s.area())
    if not pieces or any(p.area() > 0.5 for p in pieces[1:]):
        raise ValueError("The panel is missing or divided")
    sheet = pieces[0]
    # No fin may leave a stub in the OP1 lead lane or anywhere that is kept clear.
    lane = _box(origin[0] + WIRE_LANE[0], origin[1] + WIRE_LANE[1], origin[0] + WIRE_LANE[2], origin[1] + WIRE_LANE[3])
    roots = []
    for tie in ties:
        root = _root(sections, tie, origin, fin, layer)
        root.update(tie=tie, start=root["outer"] + moat)
        crossing = _oriented(root, root["inner"] - OVERLAP, root["start"], fin / 2)
        if (crossing ^ (clear + lane)).area() > 1e-6:
            raise ValueError(f"The fin at {tie} would cross a route that must stay open")
        roots.append(root)
    return dict(layer=layer, moat=moat, thickness=thickness, fin=fin, reach=reach, foot=(foot_half, foot_top),
                shadow=shadow, guard=guard, clear=clear, keep_out=keep_out, outline=outline, sheet=sheet,
                roots=roots, bed=bed, yoke_top=yoke_top)


def base54(body, panel):
    """The sacrificial base alone: panel, feet, buttresses and the six fins that reach the holder."""
    lay = layout54(body, panel)
    foot_half, foot_top = lay["foot"]
    away = _solid(lay["keep_out"], -1, 60)
    parts, necks = [_solid(lay["sheet"], 0, lay["thickness"])], []
    for root in lay["roots"]:
        half, start, height = lay["fin"] / 2, root["start"], root["height"]
        foot = _oriented(root, start, start + lay["reach"] + 2.0, foot_half) ^ lay["outline"]
        rib = _buttress(root, start, lay["reach"], half, height, foot_top)
        post = _solid(_oriented(root, start - 0.01, start + 1.2, half), 0, height)
        parts.append((_solid(foot, 0, foot_top) + rib + post) - away)
        # The fin: the only material inside the moat. It ends OVERLAP inside the holder wall.
        neck = _solid(_oriented(root, root["inner"] - OVERLAP, start + 0.01, half), 0, height)
        necks.append(neck)
    return mf.Manifold.batch_boolean(parts + necks, mf.OpType.Add), necks, lay


def backed_panel54(body, panel):
    """Return the bed-oriented holder joined to its reinforced sacrificial base as one solid."""
    base, necks, lay = base54(body, panel)
    combined = body + base
    solids = [s for s in combined.decompose() if abs(s.volume()) > 1e-6]
    if len(solids) != 1:
        raise ValueError("The base or one of its fins missed the holder")
    # The base may meet the holder only through the fins.
    stray = ((base - mf.Manifold.batch_boolean(necks, mf.OpType.Add)) ^ body).volume()
    if stray > 0.02:
        raise ValueError(f"Base material other than a fin enters the holder: {stray:.3f} mm3")
    for neck in necks:
        if (neck ^ body).volume() < 0.5:
            raise ValueError("A fin is not rooted in the holder")
    return combined


def report54(body, panel):
    """Numbers for the integration checks: areas, fin sections and where each fin is cut."""
    base, necks, lay = base54(body, panel)
    first = (body + base).slice(lay["layer"] / 2)
    rows = []
    for root, neck in zip(lay["roots"], necks):
        o, c = root["out"], root["station"]
        cut = o * root["outer"] + c
        rows.append(dict(face=root["tie"]["face"], cut_at_xy=[round(float(v), 2) for v in cut],
                         fin_thickness=lay["fin"], fin_height=round(root["height"], 2),
                         section_mm2=round(lay["fin"] * root["height"], 2),
                         rooted_volume_mm3=round(float((neck ^ body).volume()), 2)))
    return dict(holder_first_layer_mm2=round(lay["bed"].area(), 1), panel_sheet_mm2=round(lay["sheet"].area(), 1),
                combined_first_layer_mm2=round(first.area(), 1), first_layer_pieces=len(first.decompose()),
                moat_mm=lay["moat"], yoke_top_y=round(lay["yoke_top"], 2), fins=rows,
                total_fin_section_mm2=round(sum(r["section_mm2"] for r in rows), 1),
                base_volume_mm3=round(float(base.volume()), 1))
