// Compose the printed R20 parts and unchanged R19 retainers into the same menu.
// Keep their original checked recipes and show the keeper omitted from R20's
// plate. The user is still establishing real fit with that missing piece.
import { recipes as r19Recipes, assemblyPose } from '../../carbon-rod-holders-r19-lightweight/preview/assembly-recipe.mjs';
import { routePose } from '../../carbon-rod-holders-r20-finger-guard/preview/assembly-recipe.mjs';
import { identity, translated } from './assembly-data.mjs';
const r19 = new URL('../../carbon-rod-holders-r19-lightweight/exports/', import.meta.url);
const r20 = new URL('../../carbon-rod-holders-r20-finger-guard/exports/', import.meta.url);
const r21 = new URL('../../carbon-rod-holders-r21-cable-clip/exports/', import.meta.url);
const part = (baseUrl, name, label, color = '#29a5b7') => ({ file: name + '-assembly.stl', baseUrl, label, color });
const rod = (diameter = 8, length = 65, axis = 'y') => ({ primitive: { type: 'cylinder', radius: diameter / 2, length, axis }, label: 'Carbon rod', color: '#737d87', opacity: .4, frame: false });
const frames = (actors, pose) => Array.from({ length: 61 }, (_, i) => ({ ...Object.fromEntries(Object.keys(actors).map(id => [id, identity()])), ...pose(i / 60) }));
const reference = (geometry, label, color = '#78c894') => ({ geometry, label, color });
function pivotX(pivot, angle, y, z) {
  const c = Math.cos(angle), s = Math.sin(angle), [, py, pz] = pivot;
  return [1, 0, 0, 0, 0, c, -s, py - c * py + s * pz + y, 0, s, c, pz - s * py - c * pz + z];
}
async function read(url) { const response = await fetch(url); if (!response.ok) throw new Error('Printed-part guide could not be loaded'); return response.json(); }
let cached;
export function legacyR20() { return cached ||= load(); }
async function load() {
  const [old, guard, cable] = await Promise.all([read(new URL('assembly-guide.json', r19)), read(new URL('assembly-guide.json', r20)), read(new URL('manifest.json', r21))]);
  const modules = {};
  for (const kind of ['xiao', 'battery']) {
    const actors = {
      holder: part(r20, kind === 'xiao' ? 'XIAO_Rod_Holder' : 'Battery_Holder', kind === 'xiao' ? 'Printed XIAO cradle' : 'Printed battery cradle'),
      retainer: part(r19, kind === 'xiao' ? 'XIAO_Near_Keeper' : 'Battery_End_Door', kind === 'xiao' ? 'Sliding XIAO keeper' : 'Battery door', '#ee9842'),
      rod: rod(old.rod.diameter_mm, old.rod.length_mm),
    };
    if (kind === 'xiao') {
      actors.board = reference(old.geometry.board, 'XIAO board');
      for (const component of old.board.components) actors[component] = reference(old.geometry[component], component.replaceAll('_', ' '), component === 'usb_c' ? '#e5e7eb' : '#384453');
    } else {
      actors.cell = reference(old.geometry.cell, 'PKCell LP402025 maximum envelope');
      actors.spacer = part(r19, 'Battery_Spacer_0p4mm', '0.4 mm removable spacer', '#bb9ce3');
    }
    modules[kind] = {
      label: kind === 'xiao' ? 'XIAO Sense + keeper' : 'Battery + door',
      note: kind === 'xiao'
        ? 'Printed R20. The orange keeper slides into the side grooves; the tall USB-end hoop is fixed retention. R20 reused the R19 keeper rather than printing it again. Try that keeper first; clearance over your soldered wires still needs checking.'
        : 'Printed R20 uses the R19 door and spacers. Use a spacer only if the battery still slides freely; never squeeze the pouch.',
      actors,
      steps: r19Recipes[kind].map((step, index) => ({ ...step, samples: frames(actors, fraction => {
        const p = assemblyPose(kind, index, fraction, old), poses = { rod: translated(0, 10 + p.rodY, 0) };
        if (kind === 'xiao') {
          const matrix = pivotX(old.board.pivot, p.boardAngle, p.boardY, p.boardZ);
          for (const name of ['board', ...old.board.components]) poses[name] = matrix;
          poses.retainer = translated(0, p.keeperY, 0);
        } else Object.assign(poses, { cell: translated(0, p.cellY, p.cellZ), spacer: translated(0, p.cellY, 0), retainer: translated(0, 0, p.doorZ) });
        return poses;
      }) })),
    };
  }
  const keys = { holder: part(r20, 'Key_Carrier', 'Printed key holder'), rod: rod() };
  for (const [name, geometry] of Object.entries(guard.hardware)) if (/_(switch|socket)$/.test(name) && !name.includes('maximum')) keys[name] = reference(geometry, name.replaceAll('_', ' '), name.endsWith('_switch') ? '#78c894' : '#e5e7eb');
  modules.keys = { label: 'Keys + key holder', note: 'Printed R20. Socket modules load from below; bought switches enter from above. Solder outside first and keep the leads free while seating each part.', actors: keys,
    steps: [
      { title: 'Seat the Prewired Sockets', caption: 'Insert the wired sockets from below into their matching recesses. The switch and socket outlines stay at their actual dimensions.', duration: 4, samples: frames(keys, f => Object.fromEntries(Object.keys(keys).map(id => [id, translated(0, 0, id.endsWith('_socket') ? -10 * (1 - f) : id.endsWith('_switch') ? 14 : 0)]))) },
      { title: 'Press in the Switches', caption: 'Support each socket while pressing its switch into the plate from above. Keep soldered leads out of the seating faces.', duration: 4, samples: frames(keys, f => Object.fromEntries(Object.keys(keys).map(id => [id, translated(0, 0, id.endsWith('_switch') ? 14 * (1 - f) : 0)]))) },
    ] };
  const guardActors = { holder: keys.holder, guard: part(r20, 'Finger_Guard', 'Separate printed finger guard', '#ee9842'), rod: rod() };
  modules.finger_guard = { label: 'Finger guard · printed R20', note: 'This separate basket grips the rod. Its small pads bear against the key holder from underneath; they are not clips. The bulky basket is being replaced after your comfort feedback.', actors: guardActors,
    steps: [
      { title: 'Use the Open Hand End', caption: 'Slide toward the key holder from the open hand end. The guard ends just before the first carrier ring; do not force it through a ring.', duration: 6, samples: frames(guardActors, f => ({ guard: translated(0, routePose(guard, 'hand', f).offset_mm, 0) })) },
      { title: 'Rest Under the Carrier', caption: 'The little pads sit 0.3 mm below the carrier underside in the model. They bear against it under finger pressure; they do not latch on.', duration: 2, samples: frames(guardActors, () => ({})) },
    ] };
  const cp = cable.parameters;
  const cableActors = { clip: part(r21, 'Cable_Clip_4mm', 'Split figure-of-eight cable clip'), rod: rod(cp.rod_mm, 35, 'z'), wire: { primitive: { type: 'cylinder', radius: .3, length: 14, axis: 'z' }, color: '#efb86b', label: 'Illustrative 0.6 mm wire', frame: false } };
  modules.cable = { label: 'Cable clip · not yet printed', note: 'R21 has an 8 mm rod loop, a loose 4 mm cable loop and a 0.8 mm cable-entry slit. The shown thin wire is illustrative; your real bundle and insertion force are unmeasured.', actors: cableActors,
    steps: [
      { title: 'Slide onto a Bare Rod End', caption: 'Feed the bare rod end through the large loop. Do not force an 8 mm rod sideways through the narrow opening.', duration: 4, samples: frames(cableActors, f => ({ rod: translated(0, 0, -22 * (1 - f)), wire: translated(15, 0, cp.axial_width_mm / 2) })) },
      { title: 'Feed Wires through the Small Slit', caption: 'Guide thin wires in individually if needed. The animation shows one 0.6 mm wire, not a verified fit for the actual bundle. Never pinch battery leads.', duration: 4, samples: frames(cableActors, f => ({ wire: translated(15 + (cp.centres_mm - 15) * f, 0, cp.axial_width_mm / 2) })) },
    ] };
  return { schema_version: 2, revision: 'R20 printed parts and R21 cable clip', units: 'mm', physical_fit_verified: false, modules };
}
