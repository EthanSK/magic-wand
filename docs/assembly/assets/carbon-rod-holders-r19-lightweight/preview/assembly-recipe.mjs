// R19 assembly order, separate from the shared playback/camera controls.
// Distances and the board pivot come from assembly19.py and the checked CAD.
export const recipes = {
  xiao: [
    { duration: 3, title: 'Position the Board', caption: 'Remove the print pads first. Keep the USB end toward the fixed hoop, with the other end tilted slightly up.' },
    { duration: 3, title: 'Slide Under the Hoop', caption: 'Slide the USB end under the fixed hoop. Keep solder and wires outside the side rails.' },
    { duration: 3, title: 'Lower onto the Ledges', caption: 'Lower the near end onto its corner ledges. Do not press on the microphone, USB connector or solder.' },
    { duration: 3, title: 'Slide in the Keeper', caption: 'Slide the orange keeper into the two side grooves until its tooth clicks over the ridge. The small triangular holes are not keeper sockets.' },
    { duration: 4, title: 'Feed through Both Rings', caption: 'Feed a bare rod end through both rings. Do not force the rod sideways through the narrow slit. Leave the wires free.' },
  ],
  battery: [
    { duration: 3, title: 'Place on the Spacer', caption: 'Place the cell on the thin flat spacer. The 0.4 mm spacer is shown; use the thickest one that slides in without force.' },
    { duration: 4, title: 'Slide the Battery In', caption: 'Slide the battery and spacer in together, non-wire end first. The leads trail out through the door end.' },
    { duration: 3, title: 'Lower the Door', caption: 'Lower the orange door ends into the two vertical slots until the tooth clicks under the arrow bar. Keep pressure off the pouch.' },
    { duration: 4, title: 'Feed through Both Rings', caption: 'Feed a bare rod end through both rings. The grip does not need glue; insertion should not crack the rings.' },
  ],
};

const smooth = value => value * value * (3 - 2 * value);

export function assemblyPose(kind, index, fraction, data) {
  if (!recipes[kind] || !Number.isInteger(index) || index < 0 || index >= recipes[kind].length || !Number.isFinite(fraction)) throw new TypeError('Invalid assembly pose');
  const f = smooth(Math.max(0, Math.min(1, fraction)));
  if (kind === 'xiao') {
    const angle = -data.board.tilt_degrees * Math.PI / 180;
    return {
      boardAngle: index < 2 ? angle : index === 2 ? angle * (1 - f) : 0,
      boardY: index === 0 ? -data.board.slide_mm - 7 * (1 - f) : index === 1 ? -data.board.slide_mm * (1 - f) : 0,
      boardZ: index === 0 ? 18 * (1 - f) : 0,
      keeperY: index < 3 ? -data.board.keeper_travel_mm : index === 3 ? -data.board.keeper_travel_mm * (1 - f) : 0,
      rodVisible: index === 4, rodY: index === 4 ? data.rod.entry_travel_mm * (1 - f) : data.rod.entry_travel_mm,
    };
  }
  return {
    cellY: index < 1 ? -data.battery.entry_travel_mm : index === 1 ? -data.battery.entry_travel_mm * (1 - f) : 0,
    cellZ: data.battery.spacer_thickness_mm + (index === 0 ? 5 * (1 - f) : 0),
    doorZ: index < 2 ? data.battery.door_travel_mm : index === 2 ? data.battery.door_travel_mm * (1 - f) : 0,
    rodVisible: index === 3, rodY: index === 3 ? data.rod.entry_travel_mm * (1 - f) : data.rod.entry_travel_mm,
  };
}
