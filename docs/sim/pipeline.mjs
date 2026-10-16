// Wires the simulated Mac side together: Wand Receiver, Agentic Mouse's HUD and Agent Flow.
// The browser and the end-to-end test use this same wiring; only the device transport differs.
import { HudModel } from "./hud.mjs";
import { AgentFlowModel, ControlTransport, WandReceiverModel } from "./receiver.mjs";

/**
 * @param {object} options
 * @param {(command: string) => void} options.send one REPL command to the Puck
 * @param {object} options.timers {now, setTimeout, clearTimeout, setInterval, clearInterval}
 * @param {object} options.manifest wand.json
 * @param {object} options.layout data/agentic-mouse-hud.json
 * @param {import("./mac.mjs").MacScreen} options.mac
 */
export function createPipeline({ send, timers, manifest, layout, mac, onHud = () => {}, onRecording = () => {} }) {
  let receiver = null;
  // Context and recording reach the receiver over local sockets, so they arrive asynchronously.
  const later = (fn) => timers.setTimeout(fn, 0);
  const hud = new HudModel({
    layout,
    hud: manifest.hud,
    timers,
    onChange: onHud,
    onContext: (active) => later(() => receiver.setContext(active)),
  });
  const agentFlow = new AgentFlowModel({
    onRecordingChange: (active) => {
      onRecording(active);
      later(() => receiver.setRecording(active));
    },
  });
  const controls = new ControlTransport({ hud, agentFlow });
  receiver = new WandReceiverModel({ tuning: manifest.tuning, timers, controls, mac, queue: send });
  return {
    receiver,
    hud,
    agentFlow,
    controls,
    /** Feed the device's output in order: UART lines and mouse report frames. */
    handle(events) {
      for (const event of events) {
        if (event.type === "frame") receiver.handleFrame(event.x, event.y, event.b);
        else receiver.handleLine(event.text);
      }
    },
  };
}
