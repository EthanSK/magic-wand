#!/usr/bin/env python3
"""Local Sense dashboard. --hardware reads the diagnostic sketch; --receiver observes Wand Receiver. Importing opens nothing."""
import argparse, asyncio, collections, json, math, threading, time, os, socket, queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
KEYS=('thumb','index','middle')
UART_SERVICE='6e400001-b5a3-f393-e0a9-e50e24dcca9e'
UART_TX='6e400003-b5a3-f393-e0a9-e50e24dcca9e'
UART_RX='6e400002-b5a3-f393-e0a9-e50e24dcca9e'

def validate(p):
    integer=lambda v:type(v) is int and 0<=v<=0xffffffff
    if not isinstance(p,dict) or (type(p.get('schema')) is not int or p['schema']!=1) or p.get('sensor')!='wand':raise ValueError('Different firmware')
    if not all(integer(p.get(k)) for k in ('seq','ms')):raise ValueError('Invalid clock')
    if not isinstance(p.get('buttons'),dict) or not all(type(p['buttons'].get(k)) is bool for k in KEYS):raise ValueError('Missing button states')
    imu=p.get('imu','missing')
    if imu is not None and (not isinstance(imu,dict) or not all(type(imu.get(k)) in (int,float) and math.isfinite(imu[k]) and abs(imu[k])<=10000 for k in ('ax','ay','az','gx','gy','gz'))):raise ValueError('Invalid IMU')
    result={k:p[k] for k in ('schema','sensor','seq','ms')}
    result['buttons']={k:p['buttons'][k] for k in KEYS}
    result['imu']=None if imu is None else {k:imu[k] for k in ('ax','ay','az','gx','gy','gz')}
    if 'presses' in p:
        if not isinstance(p['presses'],dict) or not all(integer(p['presses'].get(k)) for k in KEYS):raise ValueError('Invalid counters')
        result['presses']={k:p['presses'][k] for k in KEYS}
    for k in ('device','firmware'):
        if isinstance(p.get(k),str) and len(p[k])<=64 and p[k].isalnum():result[k]=p[k]
    return result

class Store:
    def __init__(self,clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.rows=collections.deque(maxlen=512);self.cursor=0;self.session=0
        self.status='starting';self.message='Starting local reader';self.usb_present=False;self.bluetooth='Standby';self.transport=None;self.observer=None
    def set(self,status,message,**values):
        with self.lock:
            self.status=status;self.message=message
            for k,v in values.items():setattr(self,k,v)
    def begin(self,transport):
        with self.lock:self.session+=1;self.transport=transport;self.status='waiting';self.message=f'{transport} open; waiting for wand button packets';return self.session
    def record(self,p,transport,session):
        p=validate(p)
        with self.lock:
            if session!=self.session or transport=='Bluetooth' and self.usb_present:return False
            self.cursor+=1;self.rows.append({'id':self.cursor,'session':session,'transport':transport,'packet':p,'received':self.clock()})
            self.status='live';self.message=f'Real {transport} readings'
            return True
    def snapshot(self,after=-1):
        with self.lock:
            now=self.clock();rows=list(self.rows)
            selected=rows[-1:] if after<0 else [r for r in rows if r['id']>after]
            age=(now-rows[-1]['received'])*1000 if rows and rows[-1]['session']==self.session else None
            live=self.status=='live' and age is not None and age<1500
            return {'bridge':'wand-local-v1','status':'live' if live else 'stale' if self.status=='live' else self.status,'message':self.message if live or self.status!='live' else 'No recent wand readings','transport':self.transport,'usb_present':self.usb_present,'bluetooth':self.bluetooth,'session':self.session,'cursor':self.cursor,'age_ms':age,'packets':[{k:v for k,v in r.items() if k!='received'}|{'age_ms':max(0,(now-r['received'])*1000)} for r in selected]}

class Framer:
    def __init__(self,receive):self.buffer=bytearray();self.receive=receive;self.dropping=False
    def feed(self,data):
        for b in data:
            if b==10:
                if self.buffer and not self.dropping:
                    try:self.receive(validate(json.loads(self.buffer)))
                    except (ValueError,UnicodeError,TypeError):pass
                self.buffer.clear();self.dropping=False
            elif not self.dropping:
                self.buffer.append(b)
                if len(self.buffer)>2048:self.buffer.clear();self.dropping=True

def matching_port(p):return p.vid==0x2886 and p.pid in (0x8045,0x0045) and 'XIAO' in (p.product or '').upper()

def usb_reader(store,halt):
    import serial
    from serial.tools import list_ports
    while not halt.is_set():
        ports=[p for p in list_ports.comports() if matching_port(p)]
        with store.lock:store.usb_present=bool(ports)
        if len(ports)!=1:
            if ports:store.set('ambiguous','More than one XIAO is connected; no board selected')
            elif store.transport!='Bluetooth':store.set('searching','USB absent; looking for Magic Wand Sense on Bluetooth',transport=None)
            halt.wait(.3);continue
        if ports[0].pid==0x0045:
            store.set('bootloader','Sense is in upload mode; waiting for the running sketch',transport=None);halt.wait(.3);continue
        # Give an active BLE connection time to relinquish ownership first.
        end=time.monotonic()+2
        while store.bluetooth in ('Connecting','Connected') and time.monotonic()<end:halt.wait(.05)
        try:
            with serial.Serial(ports[0].device,115200,timeout=.15,exclusive=True) as port:
                session=store.begin('USB');frame=Framer(lambda p:store.record(p,'USB',session))
                while not halt.is_set():
                    data=port.read(max(1,min(port.in_waiting,4096)))
                    if data:frame.feed(data)
                    if not any(p.device==port.port for p in list_ports.comports()):break
        except (serial.SerialException,OSError):store.set('usb_error','USB port unavailable; close any other serial reader and reconnect',transport='USB')
        halt.wait(.3)

async def bluetooth_reader(store,halt):
    from bleak import BleakClient,BleakScanner
    while not halt.is_set():
        if store.usb_present:
            with store.lock:store.bluetooth='Standby while USB is connected'
            await asyncio.sleep(.2);continue
        try:
            with store.lock:store.bluetooth='Searching'
            found=await BleakScanner.discover(timeout=2,return_adv=True)
            if store.usb_present:continue
            matches=[d for d,a in found.values() if a.local_name=='Magic Wand Sense' and UART_SERVICE in [s.lower() for s in a.service_uuids]]
            if len(matches)!=1:
                if matches:store.set('ambiguous','More than one Magic Wand Sense advertiser; no board selected')
                await asyncio.sleep(.3);continue
            with store.lock:store.bluetooth='Connecting'
            async with BleakClient(matches[0],timeout=10) as client:
                if store.usb_present:continue
                session=store.begin('Bluetooth')
                with store.lock:store.bluetooth='Connected'
                frame=Framer(lambda p:store.record(p,'Bluetooth',session))
                await client.start_notify(UART_TX,lambda _,data:frame.feed(data))
                while client.is_connected and not store.usb_present and not halt.is_set():await asyncio.sleep(.1)
        except Exception:
            if not store.usb_present:store.set('bluetooth_error','Bluetooth unavailable or disconnected; USB remains preferred',transport=None)
            await asyncio.sleep(.5)
        finally:
            with store.lock:store.bluetooth='Standby while USB is connected' if store.usb_present else 'Searching'

RECEIVER_SOCKET=Path.home()/'Library/Application Support/WandReceiver/sense-dashboard.sock'

class ReceiverObserver:
    """Read-only view of Wand Receiver, the Sense board's one hardware owner.

    The receiver sends each accepted packet here as a same-user datagram and
    never waits for this dashboard. This observer opens no USB or Bluetooth
    connection and sends nothing back, so it cannot compete for the board or
    drive the pointer. Packets keep the wand-v1 shape the page already reads.
    """
    def __init__(self,path,store,halt):
        self.path=path;self.store=store;self.halt=halt;self.sessions={}
        if path.exists() or path.is_symlink():
            if not path.is_socket() or path.is_symlink():raise RuntimeError('Refusing to replace a file that is not a socket')
            path.unlink()
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);old=os.umask(0o177)
        try:self.sock.bind(str(path))
        finally:os.umask(old)
        os.chmod(path,0o600);self.sock.settimeout(.2)
        store.set('waiting','Waiting for Wand Receiver Sense data')
        threading.Thread(target=self.run,daemon=True).start()
    def run(self):
        while not self.halt.is_set():
            try:data=self.sock.recv(4096)
            except socket.timeout:continue
            except OSError:return
            self.receive(data)
    def receive(self,data):
        try:value=json.loads(data)
        except (ValueError,UnicodeError):return
        if not isinstance(value,dict):return
        session=value.get('session');transport=value.get('transport') if value.get('transport') in ('USB','Bluetooth') else None
        if value.get('type')=='status':
            if value.get('state')=='searching':
                self.sessions={};self.store.set('searching','Wand Receiver is looking for the Sense',transport=None,usb_present=False)
            elif value.get('state')=='live' and type(session) is int and transport:
                # Receiver session numbers restart with its process. A new live
                # boundary must reset browser sequence state even for number 1.
                self.sessions={session:self.store.begin(transport)}
                with self.store.lock:self.store.usb_present=transport=='USB'
            return
        if value.get('type')!='packet' or type(session) is not int or not transport:return
        local=self.sessions.get(session)
        if local is None:
            local=self.store.begin(transport);self.sessions={session:local}
            with self.store.lock:self.store.usb_present=transport=='USB'
        try:self.store.record(value.get('packet'),transport,local)
        except (ValueError,TypeError):pass
    def close(self):
        self.sock.close();self.path.unlink(missing_ok=True)

def make_handler(store,assets,port):
    files={'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),'/styles.css':('styles.css','text/css'),'/app.mjs':('app.mjs','text/javascript'),'/model.mjs':('model.mjs','text/javascript'),'/transports.mjs':('transports.mjs','text/javascript')}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):self.send_error(403);return
            uri=urlparse(self.path)
            if uri.path=='/api/wand':
                try:after=int(parse_qs(uri.query).get('after',['-1'])[0])
                except ValueError:self.send_error(400);return
                data=json.dumps(store.snapshot(after),allow_nan=False).encode();mime='application/json'
            elif uri.path in files:
                filename,mime=files[uri.path]
                try:data=(assets/filename).read_bytes()
                except OSError:self.send_error(404);return
                if filename=='index.html':data=data.replace(b'<html lang="en">',b'<html lang="en" data-local-bridge="1">')
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cross-Origin-Resource-Policy','same-origin');self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):self.send_error(405)
        do_PUT=do_PATCH=do_DELETE=do_POST
        def log_message(self,*_):pass
    return Handler

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8872);parser.add_argument('--assets',type=Path,default=Path(__file__).parent);parser.add_argument('--hardware',action='store_true',help='Explicitly own the Sense USB/Bluetooth connections in a private installation')
    parser.add_argument('--receiver',action='store_true',help='Observe Wand Receiver, the control firmware board owner; opens no hardware')
    parser.add_argument('--receiver-socket',type=Path,default=RECEIVER_SOCKET,help=argparse.SUPPRESS)
    args=parser.parse_args();store=Store();halt=threading.Event();server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(store,args.assets,args.port));server.daemon_threads=True
    if args.hardware and args.receiver:parser.error('choose --hardware (diagnostic sketch) or --receiver (control firmware), not both')
    if args.receiver:store.observer=ReceiverObserver(args.receiver_socket,store,halt)
    threading.Thread(target=server.serve_forever,daemon=True).start();print(f'Magic Wand live dashboard: http://127.0.0.1:{args.port}/',flush=True)
    try:
        if args.receiver:
            while True:time.sleep(1)
        elif args.hardware:
            threading.Thread(target=usb_reader,args=(store,halt),daemon=True).start();asyncio.run(bluetooth_reader(store,halt))
        else:
            store.set('disabled','Hardware readers are disabled; use the private installation workflow')
            while True:time.sleep(1)
    except KeyboardInterrupt:pass
    finally:
        halt.set();server.shutdown();server.server_close()
        if store.observer:store.observer.close()
if __name__=='__main__':main()
