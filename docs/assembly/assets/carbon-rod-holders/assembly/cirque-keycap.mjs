// Parameterized geometry for the circular module, its rounded-square seat and the flex.
const sectors = 64;
const angles = Array.from({ length: sectors }, (_, i) => 2 * Math.PI * i / sectors);

function ringShell(profile, sectionAngles) {
  const count = sectionAngles.length;
  const vertices = profile.flatMap(([radius, height]) => sectionAngles.map(angle => {
    const r = typeof radius === 'function' ? radius(angle) : radius;
    return [r * Math.cos(angle), r * Math.sin(angle), height];
  }));
  const faces = [];
  for (let row = 0; row < profile.length; row++) {
    const nextRow = (row + 1) % profile.length;
    for (let i = 0; i < count; i++) {
      const next = (i + 1) % count;
      const a = row * count + i, b = row * count + next;
      const c = nextRow * count + i, d = nextRow * count + next;
      faces.push([a, b, d], [a, d, c]);
    }
  }
  return { vertices, faces };
}

function roundedRectangleRadius(halfX, halfY, corner) {
  return angle => {
    const x = Math.abs(Math.cos(angle)), y = Math.abs(Math.sin(angle));
    const side = Math.min(halfX / x, halfY / y);
    const cx = halfX - corner, cy = halfY - corner;
    if (side * x <= cx || side * y <= cy) return side;
    const projection = x * cx + y * cy;
    return projection + Math.sqrt(projection ** 2 - cx ** 2 - cy ** 2 + corner ** 2);
  };
}

function verticalDisk(centerX, centerY, radius, bottom, top) {
  const vertices = [bottom, top].flatMap(height => angles.map(angle =>
    [centerX + radius * Math.cos(angle), centerY + radius * Math.sin(angle), height]));
  const faces = [];
  for (let i = 0; i < sectors; i++) {
    const j = (i + 1) % sectors;
    faces.push([i, j, j + sectors], [i, j + sectors, i + sectors]);
    if (i > 0 && j > 0) faces.push([0, j, i], [sectors, i + sectors, j + sectors]);
  }
  return { vertices, faces };
}

// The six conductors run along a single bending plane. Keep the cross-section
// normal to the route so the shown ribbon can curve without twisting.
function flatFlex(points, width, thickness, endTangent = [1, 0]) {
  const vertices = points.flatMap(([x, y, z], i) => {
    const before = points[Math.max(0, i - 1)];
    const after = points[Math.min(points.length - 1, i + 1)];
    // The stationary terminal fixes the last straight cross-section.
    const [dx, dz] = i === points.length - 1 ? endTangent : [after[0] - before[0], after[2] - before[2]];
    const half = thickness / (2 * Math.hypot(dx, dz));
    const ox = dz * half, oz = -dx * half;
    return [
      [x - ox, y - width / 2, z - oz], [x - ox, y + width / 2, z - oz],
      [x + ox, y + width / 2, z + oz], [x + ox, y - width / 2, z + oz],
    ];
  });
  const end = vertices.length - 4;
  const faces = [[0, 2, 1], [0, 3, 2], [end, end + 1, end + 2], [end, end + 2, end + 3]];
  for (let start = 0; start < end; start += 4) {
    for (let i = 0; i < 4; i++) {
      const next = (i + 1) % 4;
      faces.push([start + i, start + next, start + next + 4], [start + i, start + next + 4, start + i + 4]);
    }
  }
  return { vertices, faces };
}

const TRACKPAD = Object.freeze({
  radius: 8.075, pcbThickness: .89, overlayThickness: .38, depth: 5.37,
});

// GP-DS-240529 v1.3, pp. 6–7: https://www.cirque.com/documentation
// The board and component stack use the upper
// limits of the published dimensions. A local connector box is illustrative;
// Cirque's drawing doesn't dimension its offset along the PCB.
function sensorGeometry(centerX, centerY, top, connector, box) {
  const boardTop = top - TRACKPAD.overlayThickness;
  const boardBottom = boardTop - TRACKPAD.pcbThickness;
  return {
    surface: verticalDisk(centerX, centerY, 8, boardTop, top),
    board: verticalDisk(centerX, centerY, TRACKPAD.radius, boardBottom, boardTop),
    connector: box(...connector.x, ...connector.y, top - TRACKPAD.depth, boardBottom),
  };
}

// Opus's selected layout keeps the switch stroke and uses the spare width on
// the right of the switch for the module connector. The exact connector offset
// is unverified, so the preview uses a box larger than the illustrated part.
export const CIRQUE_LAYOUT = Object.freeze({
  top: 21.45, halfWidth: 9, halfLength: 8.75, switchX: -2.25,
  connectorX: [1.25, 6.25], connectorY: [-2.8, 4.8],
  dockX: 9.1, dockZ: 13.1, attachLift: 9, disconnect: .9,
  stopX: 7.4, shoulder: 1.11, pinTip: 1.61, armInner: 1.20, armOuter: 1.8, squeeze: .48,
  sensorRadius: TRACKPAD.radius, sensorDepth: TRACKPAD.depth,
});

function cableRoute(start, end) {
  // The lead exits downwards and turns towards the separable side connection.
  // This curve defines available space, with the real bend radius still open.
  const [sx, sy, sz] = start, [ex, ey, ez] = end;
  return Array.from({ length: 19 }, (_, index) => {
    const t = index / 18, u = 1 - t;
    return [
      u ** 3 * sx + 3 * u * t ** 2 * (ex - 1.1) + 3 * u ** 2 * t * sx + t ** 3 * ex,
      u * sy + t * ey,
      u ** 3 * sz + 3 * u ** 2 * t * (sz - 2) + (3 * u * t ** 2 + t ** 3) * ez,
    ];
  });
}

function transformPoint([x, y, z], pose) {
  return [0, 4, 8].map(i => pose[i] * x + pose[i + 1] * y + pose[i + 2] * z + pose[i + 3]);
}

function hingeGeometry({ box, joined, mirrored, roundPin, pinSupport, axis }) {
  const { shoulder, pinTip, armInner, armOuter, squeeze } = CIRQUE_LAYOUT;
  const [axisY, axisZ] = axis;
  const fixed = joined([-1, 1].flatMap(side => {
    const pin = roundPin(...mirrored(side, shoulder - .15, pinTip), axisY, axisZ, .65);
    pin.vertices = pin.vertices.map(([x, y, z]) => Math.abs(Math.abs(x) - pinTip) < 1e-8
      ? [x, axisY + .74 * (y - axisY), axisZ + .74 * (z - axisZ)] : [x, y, z]);
    return [
      box(...mirrored(side, .51, shoulder), 9.14, 12.9, 11.04, 19.34), pin,
      box(...mirrored(side, .44, 1.53), 9.14, 12.9, 11.04, 11.65),
    ];
  }));
  const flexed = { ...fixed, vertices: fixed.vertices.map(([x, y, z]) => {
    const t = Math.max(0, Math.min(1, (z - 11.65) / (axisZ - .65 - 11.65)));
    return [x - Math.sign(x) * squeeze * t * t * (3 - t) / 2, y, z];
  }) };
  const arms = [-1, 1].map(side => {
    const span = mirrored(side, armInner, armOuter);
    return joined([
      pinSupport(...span, axisY, axisZ, .75, 17.05, 1.23),
      box(...span, 9.05, 11.42, 19.25, 19.85),
    ]);
  });
  const openingStops = [-1, 1].map(side =>
    box(...mirrored(side, 1.18, armOuter), 10.9, 11.38, 11.04, 17));
  return { fixed, flexed, arms, openingStops };
}

export function cirqueKeycap(hingeView, boardSeat, mechanics) {
  const { box, joined, shift, sampled, capMotion, travel, freeGap } = mechanics;
  const { top, halfWidth, halfLength, switchX, connectorX, connectorY, dockX, dockZ, attachLift, disconnect, stopX } = CIRQUE_LAYOUT;
  const seat = top - TRACKPAD.overlayThickness - TRACKPAD.pcbThickness;
  const outline = roundedRectangleRadius(halfWidth, halfLength, 2);
  const roundedTop = roundedRectangleRadius(halfWidth - .14, halfLength - .14, 1.86);
  const sensor = sensorGeometry(0, 0, top, { x: connectorX, y: connectorY }, box);
  const connectorRelief = angle => {
    const x = Math.cos(angle), y = Math.sin(angle);
    if (x <= 0) return 7.25;
    const reach = Math.min(connectorX[1] / x, (y >= 0 ? connectorY[1] : connectorY[0]) / y);
    return Math.max(7.25, reach + .14);
  };
  // Include the rectangular connector's corner angles. Evenly spaced samples
  // alone can clip the relief at a corner when the renderer joins them.
  const cornerAngles = connectorX.flatMap(x => connectorY.map(y => (Math.atan2(y, x) + 2 * Math.PI) % (2 * Math.PI)));
  const sectionAngles = [...angles, ...cornerAngles].sort((a, b) => a - b);
  const shelf = ringShell([
    [outline, seat - .8], [outline, top - .28], [roundedTop, top],
    [8.175, top], [8.175, seat], [connectorRelief, seat], [connectorRelief, seat - .8],
  ], sectionAngles);
  // Keep the front beam tied into the rim and the rigid neck above the
  // flexing holder cheeks. The feet keep the established stop height.
  const beam = box(switchX - 1.2, switchX + 1.2, -8.37, -3.2, 18.2 + freeGap, 19.08);
  const frontRoot = box(switchX - 1.2, switchX + 1.2, -8.37, -7.35, 18.8, seat);
  const neck = box(-1.79, 1.79, 8.36, 11.6, 19.6, top);
  const feet = [-stopX, stopX].map(x => box(x - .63, x + .63, -4.92, -3.5, 14.2, seat));
  const cradle = joined([shelf, beam, frontRoot, neck, ...feet]);
  const ribs = joined([2.1, 3.2, 5.36].map(angle => {
    const bump = box(8.075, 8.205, -.2, .2, seat + .17, seat + .64);
    return { ...bump, vertices: bump.vertices.map(([r, tangent, z]) =>
      [r * Math.cos(angle) - tangent * Math.sin(angle), r * Math.sin(angle) + tangent * Math.cos(angle), z]) };
  }));

  const { fixed, flexed, arms, openingStops } = hingeGeometry(mechanics);
  const stopTop = Math.max(...hingeView.actors.stops.geometry.vertices.map(vertex => vertex[2]));
  const stops = joined([...openingStops, ...[-stopX, stopX].map(x => box(x - 1, x + 1, -5.1, -3.24, 11.04, stopTop))]);
  const connectorYCenter = (connectorY[0] + connectorY[1]) / 2;
  const connectorStart = [(connectorX[0] + connectorX[1]) / 2, connectorYCenter, top - TRACKPAD.depth + .12];
  const connectorEnd = [dockX, connectorYCenter, dockZ];
  const routed = cableRoute(connectorStart, connectorEnd);
  let length = 0;
  const straight = routed.map((point, index) => {
    const previous = routed[Math.max(0, index - 1)];
    length += Math.hypot(...point.map((value, axis) => value - previous[axis]));
    return [connectorStart[0], connectorStart[1], connectorStart[2] - length];
  });
  const ribbon = (points, endTangent) => flatFlex(points, 3.5, .14, endTangent);
  // The connector stays beside the carrier slab for access during removal.
  const dock = box(dockX - .38, dockX + .76, connectorYCenter - 2.1, connectorYCenter + 2.1, 11.12, dockZ + .38);
  const rails = joined([
    box(-8.42, -7.56, -16.5, 8.8, 8.7, 11.13),
    box(3.08, 3.94, -16.5, 8.8, 8.7, 11.13),
  ]);
  const actors = {
    ...hingeView.actors,
    cap: { label: 'Rounded-square touchpad cradle and click beam', color: '#a37558', geometry: cradle, cutaway: true },
    sensorSurface: { label: 'Cirque 16 mm touch surface', color: '#414b58', geometry: sensor.surface },
    sensorBoard: { label: 'Cirque sensor board', color: '#4d766c', geometry: sensor.board },
    sensorConnector: { label: 'Vertical ribbon connector envelope', color: '#e1d4bd', geometry: sensor.connector },
    ribs: { label: 'Three edge retention ribs', color: '#ca9573', geometry: ribs },
    ribbon: { label: 'Six-pin flex cable', color: '#dcac64', geometry: ribbon(routed),
      morphGeometries: [ribbon(cableRoute(transformPoint(connectorStart, capMotion(1)), connectorEnd)), ribbon(straight, [0, -1])] },
    flexDock: { label: 'Stationary ribbon connection and strain relief', color: '#70aaa3', geometry: dock },
    boardRails: { label: 'Shifted OP1 board channel', color: '#568b95', geometry: rails },
    stops: { ...hingeView.actors.stops, geometry: stops },
    hingeSupports: { label: 'Flexible holder cheeks with outward pins', color: '#67b7e7', geometry: fixed, morphGeometry: flexed },
    snapLeft: { label: 'Rigid left cap arm with pin socket', color: '#a37558', geometry: arms[0] },
    snapRight: { label: 'Rigid right cap arm with pin socket', color: '#a37558', geometry: arms[1] },
  };

  const hingeRest = hingeView.steps.at(-1).samples.at(-1);
  const rest = {
    ...hingeRest,
    ...Object.fromEntries(['sensorSurface', 'sensorBoard', 'sensorConnector', 'ribs', 'ribbon', 'flexDock', 'boardRails'].map(id => [id, hingeRest.cap])),
    ...Object.fromEntries(['board', 'plug', 'sockets'].map(id => [id, shift(boardSeat[id], switchX)])),
    body: shift(hingeRest.body, switchX),
    plunger: shift(hingeRest.plunger, switchX),
  };
  const movingSensor = ['sensorSurface', 'sensorBoard', 'sensorConnector', 'ribbon'];
  const movingCap = ['cap', 'snapLeft', 'snapRight', 'ribs', ...movingSensor];
  function installPose({ lift = 0, squeeze = 0, sensorLift = 0, ribbonDrop = 0,
    dockSlide = 0, switchLift = 0, boardSlide = 0, straightRibbon = 0 } = {}) {
    const pose = { ...rest, morphs: { hingeSupports: squeeze, ribbon: [0, straightRibbon] } };
    for (const id of movingCap) pose[id] = shift(rest[id], 0, 0, lift);
    for (const id of movingSensor) pose[id] = shift(pose[id], 0, 0, sensorLift);
    for (const id of ['board', 'plug', 'sockets']) pose[id] = shift(rest[id], 0, boardSlide);
    pose.ribbon = shift(pose.ribbon, 0, 0, -ribbonDrop);
    pose.flexDock = shift(rest.flexDock, dockSlide);
    pose.body = shift(rest.body, 0, 0, switchLift);
    pose.plunger = shift(rest.plunger, 0, 0, switchLift);
    return pose;
  }

  function pressPose(progress) {
    const pose = { ...rest, morphs: { ribbon: [progress, 0] } };
    const motion = capMotion(progress);
    for (const id of movingCap) if (id !== 'ribbon') pose[id] = motion;
    pose.plunger = shift(rest.plunger, 0, 0, -Math.max(0, travel * progress - freeGap));
    return pose;
  }

  const parked = { lift: attachLift, sensorLift: 12, ribbonDrop: 2, dockSlide: disconnect, switchLift: 7, straightRibbon: 1 };
  const steps = [
    sampled('Slide In the OP1 Board', 'Slide the socket board into the offset channel. The plug faces forward, away from the upper keys.', 2,
      progress => installPose({ ...parked, boardSlide: -7 * (1 - progress) })),
    sampled('Seat the Mouse Switch', 'Lower the OP1 switch into its sockets.', 2,
      progress => installPose({ ...parked, switchLift: 7 * (1 - progress) })),
    sampled('Connect the Touchpad Ribbon', 'Slide the ribbon into the socket underneath the touchpad.', 2,
      progress => installPose({ ...parked, switchLift: 0, ribbonDrop: parked.ribbonDrop * (1 - progress) }), true),
    sampled('Seat the Touchpad', 'Feed the straight ribbon through the opening and lower the pad onto the support ledge.', 2.3,
      progress => installPose({ ...parked, switchLift: 0, ribbonDrop: 0, sensorLift: parked.sensorLift * (1 - progress) }), true),
    sampled('Route the Ribbon', 'Curve the ribbon out beside the switch while the cap is lifted.', 1.5,
      progress => installPose({ lift: attachLift, straightRibbon: 1 - progress, dockSlide: disconnect }), true),
    sampled('Squeeze the Holder Tabs', 'Pinch the fixed holder tabs to retract their outward pins.', 1.5,
      squeeze => installPose({ lift: attachLift, squeeze, dockSlide: disconnect }), true),
    sampled('Lower the Cap', 'Lower the cap with the ribbon free of the stationary connection.', 2,
      progress => installPose({ lift: attachLift * (1 - progress), squeeze: 1, dockSlide: disconnect }), true),
    sampled('Release the Snap Pins', 'The holder pins spring outward into the rigid cap arms.', 1.5,
      progress => installPose({ squeeze: 1 - progress, dockSlide: disconnect }), true),
    sampled('Connect the Stationary End', 'Connect the fixed end beside the switch. Leave the bend free to move with the cap.', 1.7,
      progress => installPose({ dockSlide: disconnect * (1 - progress) }), true),
    sampled('Touch to Move the Pointer', 'Rest your thumb on the front half of the 14 mm sensing circle to enable pointer movement.', 1.7, () => rest),
    sampled('Press to Click', 'The pad rocks with the cradle. The OP1 switch clicks and the feet land on the holder stops.', 2, pressPose, true),
    sampled('Release the Click', 'The switch returns. Lift your thumb to pause pointer movement.', 2,
      progress => pressPose(1 - progress), true),
    sampled('Disconnect and Lift Off', 'Disconnect the ribbon, pinch the holder tabs, then lift the cap and ribbon together.', 4, progress => {
      const rise = Math.max(0, Math.min(1, (progress - .45) / .55));
      return installPose({
        dockSlide: disconnect * Math.min(1, progress / .22),
        squeeze: Math.max(0, Math.min(1, (progress - .22) / .23)),
        lift: attachLift * rise,
      });
    }, true),
  ];
  const removal = steps.at(-1);
  steps.push({ ...removal, title: 'Refit the Cap',
    caption: 'Lower the cap, release the holder pins and reconnect the stationary end.',
    samples: [...removal.samples].reverse() });
  return {
    ...hingeView, label: 'Cirque touch + click', status: 'Design preview · physical fit unverified',
    note: 'The 16 mm Cirque pad has a 14 mm sensing area. The connector and ribbon use design envelopes.',
    actors, steps,
    annotations: [
      { side: 'left', actor: 'sensorSurface', point: [0, -4, top], title: 'Touch and press here' },
      { side: 'right', actor: 'hingeSupports', point: [1.12, 12.42, 19.2], title: 'Pinch here to release' },
    ],
  };
}
