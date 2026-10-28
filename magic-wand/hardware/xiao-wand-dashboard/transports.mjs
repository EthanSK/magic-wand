// Opt-in browser readers only. No auto-connection, writes, firmware upload or OS input.
export const UART_SERVICE='6e400001-b5a3-f393-e0a9-e50e24dcca9e';
export const UART_TX='6e400003-b5a3-f393-e0a9-e50e24dcca9e';
export async function openSerial(port,onText,onEnd) {
  if (port.getInfo().usbProductId===0x0045) throw Error('That is the bootloader. Select the running Sense firmware instead.');
  await port.open({baudRate:115200});
  let reader,closing=false,terminalError;
  const decoder=new TextDecoder();
  const done=(async()=>{
    try {
      if (!port.readable) throw Error('The selected port has no readable stream.');
      reader=port.readable.getReader();
      while(!closing) { const {value,done}=await reader.read(); if(done)break; if(value)onText(decoder.decode(value,{stream:true})); }
    } catch(error) { terminalError=error; }
    finally { reader?.releaseLock(); try{await port.close();}catch{} if(!closing)onEnd(terminalError); }
  })();
  return {async close(){closing=true; try{await reader?.cancel();}catch{} await done;}};
}
export async function openBluetooth(device,onText,onEnd) {
  let characteristic,closing=false;
  const decoder=new TextDecoder();
  const receive=e=>{const v=e.target.value;onText(decoder.decode(new Uint8Array(v.buffer,v.byteOffset,v.byteLength),{stream:true}));};
  const disconnected=()=>{if(closing)return;closing=true;characteristic?.removeEventListener('characteristicvaluechanged',receive);device.removeEventListener('gattserverdisconnected',disconnected);onEnd();};
  device.addEventListener('gattserverdisconnected',disconnected);
  try {
    const server=await device.gatt.connect();
    const service=await server.getPrimaryService(UART_SERVICE);
    characteristic=await service.getCharacteristic(UART_TX);
    characteristic.addEventListener('characteristicvaluechanged',receive);
    await characteristic.startNotifications();
  } catch(error) {
    characteristic?.removeEventListener('characteristicvaluechanged',receive);
    device.removeEventListener('gattserverdisconnected',disconnected); device.gatt?.disconnect(); throw error;
  }
  return {async close(){if(closing)return;closing=true;characteristic.removeEventListener('characteristicvaluechanged',receive);device.removeEventListener('gattserverdisconnected',disconnected);try{await characteristic.stopNotifications();}catch{}device.gatt.disconnect();}};
}
