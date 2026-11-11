// Viewer-only concepts. The body, hole positions, stops and wiring are
// illustrations for comparing motion. They do not define printable geometry.
import { cirqueKeycap } from './cirque-keycap.mjs?v=cirque-cap-view';
const translate = (x = 0, y = 0, z = 0) => [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z];
const rotateBoard = [-1, 0, 0, 0, 0, -1, 0, -2, 0, 0, 1, 0];
const holeY = [-3.6, 1.6], holeZ = 13.75, bodyHalfWidth = 2.95;
const travel = .55, freeGap = .08, plungerY = -4.2;
const hingeY = 6.9, hingeZ = 18, clipHingeZ = 17.55;
const holderHingeY = 10.2;
export const UPPER_KEY_SHIFT = .86;
export const GUIDED_CAPTURE = Object.freeze({ pinZ: 17.2, pinRadius: .5, slotBottom: 16.66, slotTop: 18.37, travel });
export const HOLDER_SNAP = Object.freeze({
  axisY: holderHingeY, axisZ: hingeZ, supportInner: 1.15, supportOuter: 1.79, boreRadius: .77,
  pinTip: 1.55, pinRadius: .65, tipInner: .52, tipOuter: 1.11, squeeze: .46, rootY: 4,
});
const steps = 25;

function joined(parts) {
  const vertices = [], faces = [];
  for (const part of parts) {
    const offset = vertices.length;
    vertices.push(...part.vertices);
    faces.push(...part.faces.map(face => face.map(i => i + offset)));
  }
  return { vertices, faces };
}

function box(x0, x1, y0, y1, z0, z1) {
  const ring = z => [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]];
  const faces = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7]];
  for (let i = 0; i < 4; i++) {
    const j = (i + 1) % 4;
    faces.push([i, j, j + 4], [i, j + 4, i + 4]);
  }
  return { vertices: [...ring(z0), ...ring(z1)], faces };
}

// The two open bore walls stay visible in the mechanism view. Rings have the
// same angular samples, including the outline corners of the rectangular body.
function boreSection(y, y0, y1, z0, z1, x0 = -bodyHalfWidth, x1 = bodyHalfWidth, z = holeZ, radius = .7) {
  const directions = Array.from({ length: 24 }, (_, i) => i * Math.PI / 12);
  for (const endY of [y0, y1]) for (const endZ of [z0, z1]) {
    const angle = Math.atan2(endZ - z, endY - y);
    directions.push((angle + 2 * Math.PI) % (2 * Math.PI));
  }
  directions.sort((a, b) => a - b);
  const n = directions.length;
  const vertices = [], faces = [];
  for (const x of [x0, x1]) {
    for (const inner of [false, true]) {
      for (const angle of directions) {
        const u = Math.cos(angle), v = Math.sin(angle);
        const edge = (direction, lo, hi) => Math.abs(direction) < 1e-8 ? Infinity : (direction > 0 ? hi : lo) / direction;
        const outer = Math.min(edge(u, y0 - y, y1 - y), edge(v, z0 - z, z1 - z));
        const r = inner ? radius : outer;
        vertices.push([x, y + r * u, z + r * v]);
      }
    }
  }
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    faces.push([i, i + n, j + n], [i, j + n, j]);
    faces.push([i + 2 * n, j + 2 * n, j + 3 * n], [i + 2 * n, j + 3 * n, i + 3 * n]);
    faces.push([i + n, i + 3 * n, j + 3 * n], [i + n, j + 3 * n, j + n]);
    faces.push([i, j, j + 2 * n], [i, j + 2 * n, i + 2 * n]);
  }
  return { vertices, faces };
}

function roundPin(x0, x1, y, z, r) {
  const n = 18, vertices = [], faces = [];
  for (const x of [x0, x1]) for (let i = 0; i < n; i++) {
    const a = i * Math.PI * 2 / n;
    vertices.push([x, y + r * Math.cos(a), z + r * Math.sin(a)]);
  }
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    faces.push([i, j, j + n], [i, j + n, i + n]);
    if (i > 0 && j > 0) faces.push([0, j, i], [n, i + n, j + n]);
  }
  return { vertices, faces };
}

function claw(side) {
  const part = (a, b, ...rest) => box(Math.min(a * side, b * side), Math.max(a * side, b * side), ...rest);
  const pins = holeY.map(y => roundPin(side < 0 ? -3.35 : 2.15, side < 0 ? -2.15 : 3.35, y, holeZ, .59));
  const legs = holeY.map(y => part(3.1, 4.1, y - .75, y + .75, 13.1, 17.9));
  const rail = part(3.1, 4.2, -5.5, 7, 16.85, 18);
  const stopSupport = part(4, 6.30, -4.8, -3.65, 16.82, 17.40);
  return joined([...pins, ...legs, rail, stopSupport]);
}

const sides = [-1, 1];
const mirrored = (side, near, far) => side < 0 ? [-far, -near] : [near, far];
function pinSupport(x0, x1, y, z, r, base = z - 1.29, halfLength = 1.36) {
  return boreSection(y, y - halfLength, y + halfLength, base, z + 1.34, x0, x1, z, r);
}
function spreadArms(geometry) {
  return {
    ...geometry,
    vertices: geometry.vertices.map(([x, y, z]) => [x + Math.sign(x) * .98 * Math.max(0, Math.min(1, (16.55 - z) / 2.05)), y, z]),
  };
}
function hingeHeel(axisY, halfWidth) {
  return box(-halfWidth, halfWidth, axisY + 1.23, axisY + 1.86, 18.36, 18.84);
}
function hingeUpStop(axisY, halfWidth, cheekStart) {
  return [
    box(-halfWidth, halfWidth, axisY + 1.44, axisY + 1.92, 18.04, 18.32),
    ...sides.map(side => box(...mirrored(side, cheekStart, halfWidth), axisY + 1.27, axisY + 1.58, 18.04, 18.32)),
  ];
}
function snapArm(side) {
  // Ethan's “hinge extrusions jut facing outwards” keeps the flexible arms
  // between the fixed sockets. Squeezing them uses room inside the hinge gap.
  const { axisY, axisZ, pinTip, pinRadius, tipInner, tipOuter } = HOLDER_SNAP;
  const shoulder = pinTip - .14;
  const profiles = [
    [3.55, .27, 1.46, 17.38, 19.05],
    [4, .36, 1.37, 17.43, 18.87],
    [4.4, .42, 1.27, 17.49, 18.67],
    [4.8, .48, 1.19, 17.53, 18.56],
    [5.25, tipInner, tipOuter, 17.53, 18.56],
    [8.9, tipInner, tipOuter, 17.34, 18.61],
    [axisY - .75, tipInner, tipOuter, 17.19, 18.67],
    [axisY + 1.05, tipInner, tipOuter, 17.19, 18.67],
  ];
  const vertices = profiles.flatMap(([y, near, far, bottom, top]) => {
    const [lo, hi] = mirrored(side, near, far);
    return [[lo, y, bottom], [hi, y, bottom], [hi, y, top], [lo, y, top]];
  });
  const end = vertices.length - 4;
  const faces = [[0, 1, 2], [0, 2, 3], [end, end + 2, end + 1], [end, end + 3, end + 2]];
  for (let start = 0; start < end; start += 4) {
    for (let i = 0; i < 4; i++) {
      const j = (i + 1) % 4;
      faces.push([start + i, start + i + 4, start + j + 4], [start + i, start + j + 4, start + j]);
    }
  }
  const nose = roundPin(...mirrored(side, shoulder, pinTip), axisY, axisZ, pinRadius);
  nose.vertices = nose.vertices.map(([x, y, z]) => Math.abs(Math.abs(x) - pinTip) < 1e-8
    ? [x, axisY + (y - axisY) * .72, axisZ + (z - axisZ) * .72]
    : [x, y, z]);
  return joined([
    { vertices, faces }, nose, roundPin(...mirrored(side, .97, shoulder), axisY, axisZ, pinRadius),
    // Leave the grip faces above the sockets and behind the back of the cap.
    box(...mirrored(side, .52, tipOuter), 8.82, 9.3, 18.02, 19.77),
    box(...mirrored(side, .55, 1.05), axisY + .93, axisY + 1.72, 18.36, 18.66),
  ]);
}
function flexSnapArm(geometry) {
  const { rootY, axisY, pinRadius, squeeze } = HOLDER_SNAP;
  return { ...geometry, vertices: geometry.vertices.map(([x, y, z]) => {
    const t = Math.max(0, Math.min(1, (y - rootY) / (axisY - pinRadius - rootY)));
    return [x - Math.sign(x) * squeeze * t * t * (3 - t) / 2, y, z];
  }) };
}
function clipFrame(kind) {
  const parts = [...sides.map(claw), box(-4, 4, 5.42, 6.25, 17.5, 17.86)];
  if (kind === 'pivot') {
    parts.push(...sides.map(side => pinSupport(...mirrored(side, 2.02, 4.15), hingeY, clipHingeZ, side < 0 ? .875 : .9, 16.42)));
    parts.push(...hingeUpStop(hingeY, 3.5, 2.04));
  }
  if (kind === 'slider') {
    for (const side of sides) {
      parts.push(pinSupport(...mirrored(side, 4.20, 4.68), 0, GUIDED_CAPTURE.pinZ, .50, 16.14, 1.5));
      parts.push(pinSupport(...mirrored(side, 5.64, 6.15), 0, GUIDED_CAPTURE.pinZ, .55, 16.14, 1.5));
      parts.push(box(...mirrored(side, 4.05, 6.15), 1.1, 2.4, 16.0, 16.4));
    }
  }
  return joined(parts);
}
function slottedLugs() {
  const { slotBottom, slotTop } = GUIDED_CAPTURE;
  return joined(sides.flatMap(side => {
    const x = mirrored(side, 4.78, 5.53);
    return [
      box(...x, -1, -.58, 16.3, 18.8), box(...x, .58, 1, 16.3, 18.8),
      box(...x, -.58, .58, 16.3, slotBottom), box(...x, -.58, .58, slotTop, 18.8),
    ];
  }));
}
function sideKeeper(side) {
  const { pinZ, pinRadius } = GUIDED_CAPTURE;
  return joined([
    roundPin(...mirrored(side, 4.30, 6.16), 0, pinZ, pinRadius),
    roundPin(...mirrored(side, 6.15, 6.48), 0, pinZ, .7),
  ]);
}

function flexure(depressed) {
  return joined(sides.map(side => {
    const beam = box(...mirrored(side, 3.3, 4.15), -4, 6, 17.72, 18.13);
    return {
      ...beam,
      vertices: beam.vertices.map(([x, y, z]) => [x, y, z + (.65 - (depressed ? travel : 0)) * (6 - y) / 10]),
    };
  }));
}

const variants = {
  slider: { label: 'Guided cap', detail: 'The top moves straight down in two guides. The yellow shoulders take the load at the end of travel.' },
  flexure: { label: 'Flexible cap', detail: 'Two flexible strips let the cap move. Their stiffness adds to the force your finger feels.' },
  pivot: { label: 'Pivot on four-claw frame', axis: [hingeY, clipHingeZ], detail: 'The pin keeps the cap attached as it rocks. Press near the front edge.' },
  direct: { label: 'Pivot in switch hole', axis: [holeY[1], holeZ], detail: 'Press the near edge. The pusher slides forward as it goes down. The area behind the pivot cannot push the plunger down.' },
  carrier: { label: 'Pivot on key holder', axis: [holderHingeY, hingeZ], detail: 'The cap pivots on its two built-in pins. The feet under the cap land on low ledges in the holder to limit the press.' },
};

function directArm(side) {
  const sign = side < 0 ? [-4.35, -3.15] : [3.15, 4.35];
  return joined([
    box(...sign, 0.6, 2.6, 13.05, 18.85),
    roundPin(side < 0 ? -3.45 : 2.15, side < 0 ? -2.15 : 3.45, holeY[1], holeZ, .59),
  ]);
}

function callouts(kind, axis = [0, 0]) {
  const retention = {
    slider: { actor: 'keeperRight', point: [6.3, 0, GUIDED_CAPTURE.pinZ], title: 'Pins trap the cap' },
    flexure: { actor: 'flexure', point: [3.7, 0, 18], title: 'Strips are part of the frame' },
    pivot: { actor: 'hinge', point: [3.5, ...axis], title: 'Pin captures the hinge' },
    direct: { actor: 'rightClaws', point: [3, ...axis], title: 'Two pins in one hole' },
    carrier: { actor: 'snapRight', point: [HOLDER_SNAP.pinTip, ...axis], title: 'Pins snap outward' },
  };
  return [
    { side: 'left', actor: 'cap', point: [0, -7.5, 19.8], title: 'Press here' },
    { side: 'right', ...retention[kind] },
  ];
}

const stageY = -23, approachHeight = 9;
const shift = (pose, x = 0, y = 0, z = 0) => {
  const moved = [...pose];
  moved[3] += x;
  moved[7] += y;
  moved[11] += z;
  return moved;
};
const sampled = (title, caption, duration, pose, reveal = false) => ({
  title, caption, duration, reveal, samples: Array.from({ length: steps }, (_, i) => pose(i / (steps - 1))),
});
function capMotion(axis, progress) {
  if (!axis) return translate(0, 0, -travel * progress);
  const [axisY, axisZ] = axis;
  const angle = Math.asin(travel * progress / (axisY - plungerY));
  const c = Math.cos(angle), s = Math.sin(angle);
  return [1, 0, 0, 0, 0, c, -s, axisY * (1 - c) + axisZ * s,
    0, s, c, axisZ * (1 - c) - axisY * s];
}

export function potentialKeyViews(assembled, capGeometry) {
  const seated = assembled.steps.at(-1).samples.at(-1);
  const backgroundIds = Object.keys(assembled.actors).filter(id =>
    /^(keycap_|switch_|socket_)/.test(id) || ['carrier', 'rod', 'board', 'plug', 'sockets'].includes(id));
  const background = Object.fromEntries(backgroundIds.map(id => [id, assembled.actors[id]]));
  background.carrier = { ...background.carrier, label: 'R25 holder (layout reference)', opacity: .22 };
  const boardSeat = Object.fromEntries(backgroundIds.map(id => [id, ['board', 'plug', 'sockets'].includes(id) ? rotateBoard : seated[id]]));
  const makeActor = (label, color, geometry, properties = {}) => ({ label, color, geometry, ...properties });
  const body = makeActor('Mouse switch body (reference)', '#53405f', joined([
    boreSection(holeY[0], -7.45, -1, 10.8, 17.3), boreSection(holeY[1], -1, 5.45, 10.8, 17.3),
  ]));
  const plunger = makeActor('Switch plunger', '#ff7585', box(-.8, .8, plungerY - .6, plungerY + .6, 17, 18.2));
  const pusher = box(-1.15, 1.15, plungerY - 1.15, plungerY + 1.15, 18.2 + freeGap, 18.76);
  const wire = makeActor('Cable groove (proposed route)', '#72c1ae', {
    vertices: [[0, 23.8, 6.25], [0, 26.5, 6.25], [0, 26.5, 6.25], [5.2, 26.5, 5.4],
      [5.2, 26.5, 5.4], [7.1, 20, 2.9]],
  }, { lines: true, frame: false });
  const views = Object.fromEntries(Object.entries(variants).map(([kind, variant]) => {
    const direct = kind === 'direct', carrier = kind === 'carrier';
    const stopX = direct ? 2.65 : 5.85;
    const padHalf = carrier ? .63 : .45;
    const stopPads = [-stopX, stopX].map(x =>
      box(x - padHalf, x + padHalf, carrier ? -4.92 : -4.65, carrier ? -3.50 : -3.75, carrier ? 14.2 : 18.26, 18.75));
    const down = capMotion(variant.axis, 1);
    const stopTop = Math.min(...stopPads[0].vertices.map(([, y, z]) => down[9] * y + down[10] * z + down[11]));
    const stops = makeActor(carrier ? 'Low stop ledges on the holder' : 'Fixed travel stops', carrier ? '#389fa9' : '#e5c456',
      joined([-stopX, stopX].map(x => carrier
        ? box(x - 1, x + 1, -5.1, -3.24, 11.04, stopTop)
        : box(x - .45, x + .45, direct ? -5.2 : -4.8, -3.55, direct ? 17.3 : 16.8, stopTop))));
    const pressPad = makeActor('Moving pusher and stop pads', '#f5b577', joined([pusher, ...stopPads]));
    const pivot = kind === 'pivot', slider = kind === 'slider';
    const movingCapParts = [capGeometry, pressPad.geometry];
    if (pivot) movingCapParts.push(pinSupport(-1.85, 1.85, hingeY, clipHingeZ, .95), hingeHeel(hingeY, 1.75));
    if (slider) movingCapParts.push(slottedLugs());
    const cap = makeActor('Keycap with integral pusher', '#f3a456', joined(movingCapParts), { cutaway: true });
    const actors = { ...background, body, plunger, wire, stops, cap };
    if (direct) {
      const left = directArm(-1), right = directArm(1);
      actors.leftClaws = makeActor('Left integral pivot arm', '#67b7e7', left, { morphGeometry: spreadArms(left) });
      actors.rightClaws = makeActor('Right integral pivot arm', '#67b7e7', right, { morphGeometry: spreadArms(right) });
    } else if (!carrier) {
      const frame = clipFrame(kind);
      actors.frame = makeActor('One-piece four-claw frame', '#67b7e7', frame, { morphGeometry: spreadArms(frame) });
    }
    if (carrier) {
      const { supportInner, supportOuter, boreRadius } = HOLDER_SNAP;
      actors.hingeSupports = makeActor('Fixed hinge sockets and opening stop', '#67b7e7', joined([
        ...sides.map(side => pinSupport(...mirrored(side, supportInner, supportOuter), holderHingeY, hingeZ, boreRadius, 11.04)),
        box(-supportOuter, supportOuter, holderHingeY + 1.31, holderHingeY + 1.9, 18.04, 18.32),
      ]));
      for (const [id, side, label] of [['snapLeft', -1, 'Left'], ['snapRight', 1, 'Right']]) {
        const arm = snapArm(side);
        actors[id] = makeActor(`${label} flex arm with integral pin`, '#f3a456', arm, { morphGeometry: flexSnapArm(arm) });
      }
    }
    if (pivot) actors.hinge = makeActor('Headed clip-frame hinge pin', '#e7c768', joined([
      roundPin(-4.2, 4.16, hingeY, clipHingeZ, .875), roundPin(4.16, 4.42, hingeY, clipHingeZ, 1.06),
    ]));
    if (kind === 'flexure') actors.flexure = makeActor('Integral flexible strips', '#7ed8c0', flexure(false), { morphGeometry: flexure(true) });
    if (slider) {
      actors.keeperLeft = makeActor('Left headed keeper pin', '#e7c768', sideKeeper(-1));
      actors.keeperRight = makeActor('Right headed keeper pin', '#e7c768', sideKeeper(1));
    }
    const rest = { ...Object.fromEntries(Object.keys(actors).map(id => [id, translate()])), ...boardSeat };
    if (carrier) {
      for (const id of ['keycap_3', 'switch_3', 'socket_3', 'keycap_4', 'switch_4', 'socket_4']) {
        rest[id] = [...rest[id]];
        rest[id][3] += id.endsWith('3') ? -UPPER_KEY_SHIFT : UPPER_KEY_SHIFT;
      }
    }

    function pressPose(progress) {
      if (progress === 0) return rest;
      const moving = capMotion(variant.axis, progress);
      return {
        ...rest, cap: moving,
        ...(direct ? { leftClaws: moving, rightClaws: moving } : {}),
        ...(carrier ? { snapLeft: moving, snapRight: moving } : {}),
        plunger: translate(0, 0, -Math.max(0, travel * progress - freeGap)),
        ...(kind === 'flexure' ? { morphs: { flexure: progress } } : {}),
      };
    }
    const fits = [];
    const movingParts = ['cap', 'frame', 'stops', 'flexure', 'hinge', 'keeperLeft', 'keeperRight', 'leftClaws', 'rightClaws', 'snapLeft', 'snapRight']
      .filter(id => actors[id] && !(id === 'stops' && (carrier || direct)));
    const together = (along, lift, armFlex = 0) => {
      const pose = { ...rest, morphs: {} };
      for (const id of movingParts) pose[id] = shift(rest[id], 0, along, lift);
      for (const id of ['frame', 'leftClaws', 'rightClaws', 'snapLeft', 'snapRight']) if (actors[id]) pose.morphs[id] = armFlex;
      return pose;
    };
    const beforeMount = () => {
      const pose = together(carrier || direct ? 0 : stageY, carrier || direct ? approachHeight : 0);
      if (slider || pivot) pose.cap = shift(pose.cap, 0, 0, 7);
      if (slider) {
        pose.keeperLeft = shift(pose.keeperLeft, -5, 0, 0);
        pose.keeperRight = shift(pose.keeperRight, 5, 0, 0);
      }
      if (pivot) pose.hinge = shift(pose.hinge, 10, 0, 0);
      if (direct) {
        pose.morphs.leftClaws = 1;
        pose.morphs.rightClaws = 1;
      }
      return pose;
    };
    fits.push(sampled('Seat the Mouse Switch', 'Lower the switch into the stock board sockets. The centre-cap parts are parked clear of the board.', 1.9, progress => {
      const pose = beforeMount();
      for (const id of ['body', 'plunger']) pose[id] = shift(rest[id], 0, 0, 7 * (1 - progress));
      return pose;
    }));
    if (slider || pivot) {
      fits.push(sampled(slider ? 'Lower the Cap into the Guides' : 'Align the Hinge Holes',
        slider ? 'Lower the two slotted lugs between the blue guide walls. The keeper pins are still out.'
          : 'Lower the cap until its hinge hole lines up with the two supports.', 2.0, progress => {
          const pose = beforeMount();
          pose.cap = shift(rest.cap, 0, stageY, 7 * (1 - progress));
          return pose;
        }, true));
      fits.push(sampled(slider ? 'Slide In Both Keeper Pins' : 'Slide In the Hinge Pin',
        slider ? 'Push a headed pin through each closed slot into the snug inner frame hole. The pin stays fixed while the slot moves.'
          : 'Slide the pin through the aligned holes. The pin captures the cap, and the heel behind the hinge limits how far it opens.', 2.2, progress => {
          const pose = beforeMount();
          pose.cap = shift(rest.cap, 0, stageY, 0);
          if (slider) {
            pose.keeperLeft = shift(rest.keeperLeft, -5 * (1 - progress), stageY, 0);
            pose.keeperRight = shift(rest.keeperRight, 5 * (1 - progress), stageY, 0);
          } else pose.hinge = shift(rest.hinge, 10 * (1 - progress), stageY, 0);
          return pose;
        }, true));
    }
    if (slider) fits.push(sampled('Check the Cap Is Captive',
      'Lift the cap. The bottoms of the closed slots catch the two fixed pins, so the cap stays with the frame.', 1.4, progress => {
        const pose = together(stageY, 0);
        pose.cap = shift(pose.cap, 0, 0, .04 * Math.sin(progress * Math.PI));
        return pose;
      }, true));
    if (kind === 'flexure') fits.push(sampled('See the One-Piece Cap',
      'The two strips join the cap to the clip frame. They bend during a press and keep the cap attached when released.', 1.4,
      () => together(stageY, 0), true));
    if (carrier) {
      fits.push(sampled('Squeeze Both Arms In', 'Pinch the tabs to pull the pins between the two fixed sockets.', 1.6,
        progress => together(0, approachHeight, progress), true));
      fits.push(sampled('Lower the Cap onto the Hinge', 'Keep the arms squeezed and lower the cap until the pins line up with the sockets.', 2,
        progress => together(0, approachHeight * (1 - progress), 1), true));
      fits.push(sampled('Let the Pins Snap Outward', 'Release the tabs. The pins move outward into the sockets and the cap can pivot.', 1.6,
        progress => together(0, 0, 1 - progress), true));
      fits.push(sampled('Remove and Refit the Cap', 'Pinch the tabs before lifting. Lower the cap again and let the pins snap back into the sockets.', 4, progress => {
        const out = 1 - Math.abs(2 * progress - 1);
        return together(0, approachHeight * Math.max(0, (out - .35) / .65), Math.min(1, out / .35));
      }, true));
    } else if (!direct) {
      fits.push(sampled('Bring the Assembly over the Switch', 'Lift the assembled cap and frame, then bring it over the switch.', 2.1, progress => {
        const lift = approachHeight * Math.min(1, progress * 2);
        return together(stageY * (1 - Math.max(0, progress * 2 - 1)), lift);
      }));
    }
    if (!carrier) {
      fits.push(sampled(direct ? 'Snap the Two Pivot Arms In' : 'Snap the Frame onto the Switch',
        direct ? 'Spread the two arms, lower the cap, then let the pins snap into the rear body hole.'
          : 'Spread the four claws, lower the frame, then release the claws into both switch holes.', 2.7, progress => {
          const lift = approachHeight * (1 - Math.max(0, Math.min(1, (progress - .25) * 2)));
          const spread = Math.min(1, (direct ? 1 : progress * 4), (1 - progress) * 4);
          return together(0, lift, spread);
        }, true));
    }
    return [`concept_${kind}`, {
      label: variant.label, concept: true, openSeated: true, rotation: [.9, 0, .27],
      status: direct ? 'Needs a switch hold-down' : 'Concept · fit unverified',
      comparisonOnly: direct,
      note: direct ? 'This pivot needs a switch hold-down and only works near the front edge.' : 'The hardware dimensions and printed fit still need checking.',
      actors, annotations: callouts(kind, variant.axis),
      steps: [
        ...fits,
        sampled('Press the Cap', variant.detail, 2, pressPose, true),
        sampled('Release the Cap', 'The plunger returns. The cap stays attached to its mount.', 2, progress => pressPose(1 - progress), true),
      ],
    }];
  }));
  views.concept_touch = cirqueKeycap(views.concept_carrier, seated, {
    box, joined, mirrored, roundPin, pinSupport, shift, sampled, travel, freeGap,
    axis: [holderHingeY, hingeZ], capMotion: progress => capMotion([holderHingeY, hingeZ], progress),
  });
  return views;
}
