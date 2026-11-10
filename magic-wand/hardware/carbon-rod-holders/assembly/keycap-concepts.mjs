// Viewer-only concepts. The body, hole positions, stops and wiring are
// illustrations for comparing motion. They do not define printable geometry.
const translate = (x = 0, y = 0, z = 0) => [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z];
const rotateBoard = [-1, 0, 0, 0, 0, -1, 0, -2, 0, 0, 1, 0];
const holeY = [-3.6, 1.6], holeZ = 13.75, bodyHalfWidth = 2.95;
const travel = .55, freeGap = .08, plungerY = -4.2;
const hingeY = 6.5, hingeZ = 18;
const holderHingeY = 10.1;
export const UPPER_KEY_SHIFT = 1.15;
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
function boreSection(y, y0, y1, z0, z1) {
  const directions = Array.from({ length: 24 }, (_, i) => i * Math.PI / 12);
  for (const endY of [y0, y1]) for (const endZ of [z0, z1]) {
    const angle = Math.atan2(endZ - holeZ, endY - y);
    directions.push((angle + 2 * Math.PI) % (2 * Math.PI));
  }
  directions.sort((a, b) => a - b);
  const n = directions.length;
  const vertices = [], faces = [];
  for (const x of [-bodyHalfWidth, bodyHalfWidth]) {
    for (const inner of [false, true]) {
      for (const angle of directions) {
        const u = Math.cos(angle), v = Math.sin(angle);
        const edge = (direction, lo, hi) => Math.abs(direction) < 1e-8 ? Infinity : (direction > 0 ? hi : lo) / direction;
        const outer = Math.min(edge(u, y0 - y, y1 - y), edge(v, z0 - holeZ, z1 - holeZ));
        const r = inner ? .7 : outer;
        vertices.push([x, y + r * u, holeZ + r * v]);
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

function claw(side, kind) {
  const part = (a, b, ...rest) => box(Math.min(a * side, b * side), Math.max(a * side, b * side), ...rest);
  const pins = holeY.map(y => roundPin(side < 0 ? -3.35 : 2.15, side < 0 ? -2.15 : 3.35, y, holeZ, .59));
  const legs = holeY.map(y => part(3.1, 4.1, y - .75, y + .75, 13.1, 17.9));
  const rail = part(3.1, 4.2, -5.5, 7, 16.85, 18);
  const attachment = kind === 'pivot'
    ? part(4.15, 5.35, 5.5, 7.45, 16.75, 18.9)
    : part(4.15, 5.2, -5.5, 5.5, 16.8, kind === 'slider' ? 18.3 : 17.8);
  return joined([...pins, ...legs, rail, attachment]);
}

function flexure(depressed) {
  return joined([-1, 1].map(side => {
    const beam = box(side < 0 ? -5.85 : 4.75, side < 0 ? -4.75 : 5.85, -4, 6, 18, 18.65);
    return {
      ...beam,
      vertices: beam.vertices.map(([x, y, z]) => [x, y, z - (depressed ? travel * (6 - y) / 10 : 0)]),
    };
  }));
}

const variants = {
  slider: { label: 'Guided cap', detail: 'The top moves straight down in two guides. The yellow shoulders take the load at the end of travel.' },
  flexure: { label: 'Flexible cap', detail: 'Two flexible strips let the cap move. Their stiffness adds to the force your finger feels.' },
  pivot: { label: 'Pivot on four-claw frame', axis: [hingeY, hingeZ], detail: 'A short pin on the clip frame lets the cap rock like a mouse button. The front edge has the most travel.' },
  direct: { label: 'Pivot in switch hole', axis: [holeY[1], holeZ], detail: 'Press the near edge. The pusher slides forward as it goes down. The area behind the pivot cannot push the plunger down.' },
  carrier: { label: 'Pivot on key holder', axis: [holderHingeY, hingeZ], detail: 'The narrow arm passes between the upper keys, shifted out 1.15 mm each. The hinge transfers load to the holder.' },
};

function directArm(side) {
  const sign = side < 0 ? [-4.35, -3.15] : [3.15, 4.35];
  return joined([
    box(...sign, 0.6, 2.6, 13.05, 18.85),
    roundPin(side < 0 ? -3.45 : 2.15, side < 0 ? -2.15 : 3.45, holeY[1], holeZ, .59),
  ]);
}

function callouts(kind, variant) {
  const labels = [
    { side: 'left', actor: 'cap', point: [0, -7.5, 19.8], title: 'Thumb here', text: 'The lower edge lines up with the outer caps.' },
    { side: 'right', actor: 'plunger', point: [0, plungerY, 18.2], title: 'Mouse switch plunger',
      text: kind === 'direct' ? 'The low pivot makes the pusher sweep about 0.4 mm sideways.' : 'The pusher moves almost straight down.' },
    { side: 'right', actor: 'stops', point: [kind === 'direct' ? 2.65 : 5.85, -4.2, 17.71], title: 'Down-stop',
      text: 'This shoulder is meant to take the load after the click.' },
    { side: 'left', actor: 'plug', point: [0, -22, 5.5], title: 'Plug and wire groove',
      text: 'The board turns 180° so the wire exits towards the upper row.' },
  ];
  if (variant.axis) {
    const [y, z] = variant.axis;
    const lever = `${(y - plungerY).toFixed(1)} mm to the switch · ${(y + 7.5).toFixed(1)} mm to your thumb.`;
    labels.unshift({
      side: 'right', actor: kind === 'direct' ? 'rightClaws' : 'hinge', point: [kind === 'direct' ? 3 : 0, y, z],
      title: kind === 'direct' ? 'Pivot in one body hole' : 'Fixed hinge',
      text: `Model estimate. ${lever} ${kind === 'direct' ? 'Light at the near edge, much stiffer at the centre.' : 'More thumb travel makes the near edge lighter.'}`,
    });
  } else {
    labels.unshift({
      side: 'right', actor: 'rightClaws', point: [3.7, holeY[1], holeZ], title: 'Four fixed claws',
      text: 'Two short pins enter each body hole from opposite sides. The top moves independently.',
    });
  }
  if (kind === 'flexure' || kind === 'slider') {
    labels.splice(2, 0, {
      side: 'left', actor: kind === 'flexure' ? 'flexure' : 'guides', point: [5.3, 1, 18.2],
      title: kind === 'flexure' ? 'Flexible strips' : 'Straight guides',
      text: kind === 'flexure' ? 'They bend as you press. Stiffer strips make the click heavier.' : 'The cap travels about as far as the plunger. Guide friction adds force.',
    });
  }
  return labels;
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
  return Object.fromEntries(Object.entries(variants).map(([kind, variant]) => {
    const direct = kind === 'direct', carrier = kind === 'carrier';
    const stopX = direct ? 2.65 : 5.85;
    const stopPads = [-stopX, stopX].map(x => box(x - .45, x + .45, -4.65, -3.75, 18.26, 18.75));
    const stops = makeActor('Fixed travel stops', '#e5c456', joined([-stopX, stopX].map(x =>
      box(x - .45, x + .45, -4.8, -3.65, direct ? 17.3 : 16.8, 17.71))));
    const pressPad = makeActor('Moving pusher and stop pads', '#f5b577', joined([pusher, ...stopPads]));
    const cap = makeActor('Moving keycap', '#f3a456', carrier ? joined([
      capGeometry, box(-1.35, 1.35, 6.9, holderHingeY + .8, 17.12, 19.08),
    ]) : capGeometry, { cutaway: true });
    const actors = {
      ...background, body, plunger, wire,
      stops, cap, pressPad,
    };
    if (!carrier) {
      actors.leftClaws = makeActor(direct ? 'Left pivot arm' : 'Left claws (two pins)', '#67b7e7', direct ? directArm(-1) : claw(-1, kind));
      actors.rightClaws = makeActor(direct ? 'Right pivot arm' : 'Right claws (two pins)', '#67b7e7', direct ? directArm(1) : claw(1, kind));
    }
    if (carrier) actors.hingeSupports = makeActor('Hinge supports on key holder', '#67b7e7', joined([
      box(-2.02, -1.48, holderHingeY - .95, holderHingeY + .95, 11.04, 19),
      box(1.48, 2.02, holderHingeY - .95, holderHingeY + .95, 11.04, 19),
    ]));
    if (carrier) actors.hinge = makeActor('Pivot pin on key holder', '#e7c768', roundPin(-2.06, 2.06, holderHingeY, hingeZ, .875));
    if (kind === 'pivot') actors.hinge = makeActor('Pivot pin on clip frame', '#e7c768', roundPin(-5.4, 5.4, hingeY, hingeZ, .875));
    if (kind === 'flexure') actors.flexure = makeActor('Flexible strips', '#7ed8c0', flexure(false), { morphGeometry: flexure(true) });
    if (kind === 'slider') actors.guides = makeActor('Moving guides', '#82c8ec', joined([
      box(-5.55, -5.22, -3.5, 4.5, 16.9, 18.7), box(5.22, 5.55, -3.5, 4.5, 16.9, 18.7),
    ]));
    const rest = { ...Object.fromEntries(Object.keys(actors).map(id => [id, translate()])), ...boardSeat };
    if (carrier) {
      for (const id of ['keycap_3', 'switch_3', 'socket_3', 'keycap_4', 'switch_4', 'socket_4']) {
        rest[id] = [...rest[id]];
        rest[id][3] += id.endsWith('3') ? -UPPER_KEY_SHIFT : UPPER_KEY_SHIFT;
      }
    }

    function pressPose(progress) {
      if (progress === 0) return rest;
      let moving = translate(0, 0, -travel * progress);
      if (variant.axis) {
        const [axisY, axisZ] = variant.axis;
        const angle = Math.asin(travel * progress / (axisY - plungerY));
        const c = Math.cos(angle), s = Math.sin(angle);
        moving = [1, 0, 0, 0, 0, c, -s, axisY * (1 - c) + axisZ * s,
          0, s, c, axisZ * (1 - c) - axisY * s];
      }
      return {
        ...rest, cap: moving, pressPad: moving, ...(kind === 'slider' ? { guides: moving } : {}),
        ...(direct ? { leftClaws: moving, rightClaws: moving } : {}),
        plunger: translate(0, 0, -Math.max(0, travel * progress - freeGap)),
        ...(kind === 'flexure' ? { morphs: { flexure: progress } } : {}),
      };
    }
    function fitPose(progress) {
      const lift = 6 * Math.max(0, 1 - progress * 1.5);
      const spread = .95 * (1 - Math.max(0, progress * 3 - 2));
      const pose = { ...rest };
      if (!carrier) Object.assign(pose, { leftClaws: translate(-spread, 0, lift), rightClaws: translate(spread, 0, lift) });
      for (const id of ['cap', 'pressPad', 'hinge', 'guides', 'flexure', 'stops']) {
        if (actors[id] && !(carrier && id === 'stops') && !(direct && id === 'stops')) pose[id] = translate(0, 0, lift);
      }
      return pose;
    }
    const samples = mapper => Array.from({ length: steps }, (_, i) => mapper(i / (steps - 1)));
    return [`concept_${kind}`, {
      label: variant.label, concept: true, openSeated: true, rotation: [.9, 0, .27],
      note: 'Concept preview. The switch holes, plug clearance and 0.55 mm pusher movement are estimates. The translucent holder shows the current layout.',
      actors, annotations: callouts(kind, variant),
      steps: [
        {
          title: carrier ? 'Fit the Cap and Hinge' : 'Clip onto the Switch',
          caption: carrier ? 'Seat the cap above the rotated board. The two blue supports carry the pin on the upper edge.'
            : direct ? 'Spread the two blue arms, then seat both pins in the rear switch hole.'
            : 'Spread the blue arms, lower the frame and let its four short pins seat in the two body holes.',
          duration: 2.8, samples: samples(fitPose),
        },
        { title: 'Press the Cap', caption: variant.detail, duration: 2, samples: samples(pressPose) },
        { title: 'Release the Cap', caption: 'The plunger returns and the top comes back up. The mount stays seated.', duration: 2, samples: samples(progress => pressPose(1 - progress)) },
      ],
    }];
  }));
}
