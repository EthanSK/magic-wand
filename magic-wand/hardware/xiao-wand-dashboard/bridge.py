#!/usr/bin/env python3
"""Local Sense dashboard. --hardware reads the diagnostic sketch; --receiver observes Wand Receiver. Importing opens nothing."""
import argparse, asyncio, collections, ctypes, json, math, threading, time, os, socket, stat, uuid, queue, logging, logging.handlers
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
    for k,low,high in [('imuFlags',0,3),('sampleCount',1,255),('firstMicros',0,0xffffffff)]:
        if k in p:
            if type(p[k]) is not int or not low<=p[k]<=high:raise ValueError('Invalid sample metadata')
            result[k]=p[k]
    return result

def accepted_usage(value):
    # Actual posted pointer travel, not inferred use from a moving gyro.
    if not isinstance(value,dict):return None
    if type(value.get('pointerPosts')) is not int or value['pointerPosts']<0:return None
    travel=value.get('pointerTravel')
    if type(travel) not in (int,float) or not math.isfinite(travel) or travel<0:return None
    if not all(type(value.get(k)) is bool for k in ('follow','paused','recording','hud')):return None
    if value.get('pointerPath') not in ('direct','tuned'):return None
    result={k:value[k] for k in ('pointerPosts','pointerTravel','follow','paused','recording','hud','pointerPath')}
    # Late readings the receiver kept out of normal pointing (no catch-up replay).
    if type(value.get('lateDropped')) is int and value['lateDropped']>=0:result['lateDropped']=value['lateDropped']
    return result

class PrivateReadingsHandler(logging.handlers.RotatingFileHandler):
    failed=False
    def _open(self):
        fd=os.open(self.baseFilename,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid():
            os.close(fd);raise OSError('Private readings file required')
        os.fchmod(fd,0o600)
        return os.fdopen(fd,'a',encoding='utf-8')
    def handleError(self,record):self.failed=True

class RollingReadings:
    """Automatic recent sensor history; bounded, private, off the receive path.

    Ethan's 'real life footage' means readings from actual use. Keep the raw
    history and explicit pointer-post counters, so still/unused time is never
    mislabeled as a mouse test. No screen, audio, text or app titles are captured.
    """
    def __init__(self,path,max_bytes=8*1024*1024,backups=7,clock=time.time,capture_seconds=600,retention_seconds=7200):
        backups=max(0,min(31,backups))
        path=Path(path);path.mkdir(parents=True,exist_ok=True,mode=0o700)
        if path.is_symlink() or path.stat().st_uid!=os.geteuid() or path.stat().st_mode&0o077:
            raise ValueError('Private recording directory required')
        self.path=path;self.clock=clock;self.purged=False
        self.queue=queue.Queue(maxsize=1024);self.dropped=0;self.error=False
        self.capture_until=0;self.delete_after=0;self.capture_enabled=False;self.next_check=0
        # Persist wall-clock deadlines. Reopening the dashboard or reconnecting
        # the wand must never grant an expired capture another ten minutes.
        state=path/'capture-window.json';self.state=state
        try:
            if not state.exists():
                now=clock();data=json.dumps({'captureUntil':now+capture_seconds,'deleteAfter':now+capture_seconds+retention_seconds})
                fd=os.open(state,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
                with os.fdopen(fd,'w') as f:f.write(data)
            self.reload_window()
        except (OSError,ValueError,KeyError,TypeError):self.error=True
        self.handler=PrivateReadingsHandler(path/'readings.jsonl',maxBytes=max_bytes,backupCount=backups,encoding='utf-8',delay=True)
        self.maximum_bytes=max_bytes*(backups+1)
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    @property
    def enabled(self):return self.capture_enabled and not self.error and self.clock()<self.capture_until
    @property
    def status(self):return dict(enabled=self.enabled,dropped=self.dropped,error=self.error or self.handler.failed,captureUntil=self.capture_until,deleteAfter=self.delete_after,maximumBytes=self.maximum_bytes)
    def record(self,row):
        if not self.enabled:return
        value={k:v for k,v in row.items() if k!='received'}
        value.update(poll=row['received'],age_ms=0,wallTime=self.clock(),captureDrops=self.dropped)
        try:self.queue.put_nowait(value)
        except queue.Full:self.dropped+=1
    def reload_window(self):
        info=self.state.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o077 or info.st_size>1024:raise ValueError('Untrusted recording deadline')
        value=json.loads(self.state.read_text());end=value['captureUntil'];delete=value['deleteAfter']
        if not all(type(x) in (int,float) and math.isfinite(x) for x in (end,delete)) or delete<end:raise ValueError('Invalid recording deadline')
        if (end,delete)!=(self.capture_until,self.delete_after):self.purged=False
        self.capture_until=end;self.delete_after=delete;self.capture_enabled=value.get('enabled',True) is True
    def maintain(self):
        if self.clock()>=self.next_check:
            self.next_check=self.clock()+1
            try:self.reload_window()
            except (OSError,ValueError,KeyError,TypeError):self.capture_enabled=False
        if self.purged or self.error or self.clock()<self.delete_after:return
        self.handler.close()
        # Only this recorder's fixed filenames are eligible. Never traverse or
        # remove saved reference folders, symlinks, or unrelated diagnostics.
        for index in range(32):
            p=self.path/('readings.jsonl' if index==0 else f'readings.jsonl.{index}')
            try:
                info=p.lstat()
                if stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid():p.unlink()
            except FileNotFoundError:pass
        self.purged=True
    def run(self):
        while True:
            try:self.maintain()
            except OSError:self.error=True
            try:value=self.queue.get(timeout=1)
            except queue.Empty:continue
            try:
                if value is None:return
                if not self.purged and value['wallTime']<self.capture_until and self.clock()<self.delete_after:
                    self.handler.emit(logging.LogRecord('wand-readings',logging.INFO,'',0,json.dumps(value,allow_nan=False,separators=(',',':')),(),None))
            except Exception:self.error=True
            finally:self.queue.task_done()
    def close(self):
        self.queue.join();self.queue.put(None);self.thread.join(timeout=2);self.handler.close()

class Store:
    def __init__(self,clock=time.monotonic,recorder=None):
        self.recorder=recorder
        self.clock=clock;self.lock=threading.Lock();self.rows=collections.deque(maxlen=512);self.cursor=0;self.session=0
        self.status='starting';self.message='Starting local reader';self.usb_present=False;self.bluetooth='Standby';self.transport=None;self.observer=None
    def set(self,status,message,**values):
        with self.lock:
            self.status=status;self.message=message
            for k,v in values.items():setattr(self,k,v)
    def begin(self,transport):
        with self.lock:self.session+=1;self.transport=transport;self.status='waiting';self.message=f'{transport} open; waiting for wand button packets';return self.session
    def record(self,p,transport,session,usage=None):
        p=validate(p)
        with self.lock:
            if session!=self.session or transport=='Bluetooth' and self.usb_present:return False
            self.cursor+=1;row={'id':self.cursor,'session':session,'transport':transport,'packet':p,'received':self.clock()}
            context=accepted_usage(usage)
            if context is not None:row['usage']=context
            self.rows.append(row)
            self.status='live';self.message=f'Real {transport} readings'
        if self.recorder:self.recorder.record(row)
        return True
    def snapshot(self,after=-1):
        with self.lock:
            now=self.clock();rows=list(self.rows)
            selected=rows[-1:] if after<0 else [r for r in rows if r['id']>after]
            age=(now-rows[-1]['received'])*1000 if rows and rows[-1]['session']==self.session else None
            live=self.status=='live' and age is not None and age<1500
            return {'bridge':'wand-local-v1','status':'live' if live else 'stale' if self.status=='live' else self.status,'message':self.message if live or self.status!='live' else 'No recent wand readings','transport':self.transport,'usb_present':self.usb_present,'bluetooth':self.bluetooth,'session':self.session,'cursor':self.cursor,'age_ms':age,'capture':self.recorder.status if self.recorder else {'enabled':False,'dropped':0,'error':False},'packets':[{k:v for k,v in r.items() if k!='received'}|{'age_ms':max(0,(now-r['received'])*1000)} for r in selected]}

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
        try:self.store.record(value.get('packet'),transport,local,value.get('usage'))
        except (ValueError,TypeError):pass
    def close(self):
        self.sock.close();self.path.unlink(missing_ok=True)

RECEIVER_SUPPORT=RECEIVER_SOCKET.parent
ACTION_REQUEST='actions-pause.request'

def receiver_running(pid):
    """True only for a live process whose executable is Wand Receiver; no signal is sent."""
    if type(pid) is not int or pid<=1:return False
    try:
        buffer=ctypes.create_string_buffer(4096)
        if ctypes.CDLL('/usr/lib/libproc.dylib').proc_pidpath(pid,buffer,4096)<=0:return False
    except OSError:return False
    return os.path.basename(buffer.value.decode(errors='replace'))=='WandReceiver'

def read_receiver_status(support):
    """The receiver's own status.json: same-user regular file only."""
    path=support/'status.json'
    try:
        info=os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or info.st_size>65536:return None
        value=json.loads(path.read_bytes())
    except (OSError,ValueError,UnicodeError):return None
    return value if isinstance(value,dict) else None

class ActionControl:
    """Ethan's debug pause, owned by Wand Receiver, not this page.

    The page only displays the receiver's reported state. A request is a private
    same-user file in the receiver's directory; the receiver applies it and echoes
    its id in status.json. No code, hardware connection or new port is involved.
    """
    def __init__(self,support=RECEIVER_SUPPORT,alive=receiver_running,clock=time.monotonic,sleep=time.sleep,wall=time.time):
        self.support=support;self.alive=alive;self.clock=clock;self.sleep=sleep;self.wall=wall;self.lock=threading.Lock()
    def state(self,status=None):
        status=read_receiver_status(self.support) if status is None else status
        pid=status.get('pid') if status else None
        if type(pid) is not int or not self.alive(pid):return {'available':False,'paused':None}
        paused=status.get('actionsPaused')
        # A receiver without this feature is unavailable, never reported as paused or active.
        if type(paused) is not bool:return {'available':False,'paused':None}
        since=status.get('actionsPausedAt')
        path=status.get('pointerPath')
        return {'available':True,'paused':paused,'since':since if paused and type(since) in (int,float) else None,'ready':status.get('ready') is True,
                'pointerPath':path if path in ('direct','tuned') else None,'connected':status.get('connected') is True,'battery':self.battery(status)}
    def battery(self,status):
        # The receiver's voltage-derived estimate. Runtime is not measured, so none is offered.
        value=status.get('battery')
        if not isinstance(value,dict):return None
        percent,volts,measured=value.get('percent'),value.get('volts'),value.get('measuredAt')
        if type(percent) is not int or not 0<=percent<=100 or type(volts) not in (int,float) or not 1<=volts<=5 or type(measured) not in (int,float):return None
        return {'percent':percent,'volts':round(volts,2),'ageSeconds':max(0,round(self.wall()-measured))}
    def request(self,paused,timeout=2.0):
        with self.lock:
            if not self.state()['available']:return 503,{'available':False,'paused':None,'confirmed':False}
            request=uuid.uuid4().hex
            data=json.dumps({'version':1,'paused':paused,'id':request},separators=(',',':')).encode()
            target=self.support/ACTION_REQUEST;temporary=self.support/f'.{ACTION_REQUEST}.{request}'
            try:
                fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
                try:os.write(fd,data)
                finally:os.close(fd)
                os.replace(temporary,target)
            except OSError:
                try:os.unlink(temporary)
                except OSError:pass
                return 503,{**self.state(),'confirmed':False}
            end=self.clock()+timeout
            while self.clock()<end:
                status=read_receiver_status(self.support)
                if status and status.get('actionsRequest')==request:return 200,{**self.state(status),'confirmed':True}
                self.sleep(.05)
            # Never leave an unapplied request for a later receiver to act on.
            try:
                if target.read_bytes()==data:target.unlink()
            except OSError:pass
            return 504,{**self.state(),'confirmed':False}

def parse_action_post(headers,body,port):
    """Validate one same-origin pause request. Returns (status, paused or error)."""
    origins=(f'http://127.0.0.1:{port}',f'http://localhost:{port}')
    if headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):return 403,'host'
    if headers.get('Origin') not in origins or headers.get('Origin') != f"http://{headers.get('Host')}":return 403,'origin'
    if headers.get('Sec-Fetch-Site') not in (None,'same-origin'):return 403,'site'
    if (headers.get('Content-Type') or '').split(';')[0].strip().lower()!='application/json':return 415,'type'
    if body is None or len(body)>64:return 413,'size'
    try:value=json.loads(body)
    except (ValueError,UnicodeError):return 400,'json'
    if not isinstance(value,dict) or set(value)!={'paused'} or type(value['paused']) is not bool:return 400,'shape'
    return 200,value['paused']

def make_handler(store,assets,port,actions=None):
    files={'/':('index.html','text/html; charset=utf-8'),'/index.html':('index.html','text/html; charset=utf-8'),'/styles.css':('styles.css','text/css'),'/app.mjs':('app.mjs','text/javascript'),'/model.mjs':('model.mjs','text/javascript'),'/transports.mjs':('transports.mjs','text/javascript')}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):self.send_error(403);return
            uri=urlparse(self.path)
            if uri.path=='/api/actions':
                data=json.dumps(actions.state() if actions else {'available':False,'paused':None},allow_nan=False).encode();mime='application/json'
            elif uri.path=='/api/wand':
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
        def reply(self,code,value):
            data=json.dumps(value,allow_nan=False).encode()
            self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cross-Origin-Resource-Policy','same-origin');self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_POST(self):
            # Only the debug pause is writable, and only in --receiver mode.
            if urlparse(self.path).path!='/api/actions':self.send_error(405);return
            if actions is None:self.send_error(409);return
            try:length=int(self.headers.get('Content-Length',''))
            except ValueError:self.send_error(411);return
            body=self.rfile.read(length) if 0<=length<=64 else None
            code,value=parse_action_post(self.headers,body,port)
            if code!=200:self.send_error(code);return
            self.reply(*actions.request(value))
        def do_PUT(self):self.send_error(405)
        do_PATCH=do_DELETE=do_PUT
        def log_message(self,*_):pass
    return Handler

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8872);parser.add_argument('--assets',type=Path,default=Path(__file__).parent);parser.add_argument('--hardware',action='store_true',help='Explicitly own the Sense USB/Bluetooth connections in a private installation')
    parser.add_argument('--receiver',action='store_true',help='Observe Wand Receiver, the control firmware board owner; opens no hardware')
    parser.add_argument('--receiver-socket',type=Path,default=RECEIVER_SOCKET,help=argparse.SUPPRESS)
    parser.add_argument('--record-dir',type=Path,default=RECEIVER_SUPPORT/'DebugReadings',help='Private rolling sensor recordings in receiver mode')
    parser.add_argument('--no-record',action='store_true',help='Disable automatic receiver-mode readings history')
    args=parser.parse_args()
    if args.hardware and args.receiver:parser.error('choose --hardware (diagnostic sketch) or --receiver (control firmware), not both')
    recorder=RollingReadings(args.record_dir) if args.receiver and not args.no_record else None
    store=Store(recorder=recorder);halt=threading.Event();server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(store,args.assets,args.port,ActionControl(args.receiver_socket.parent) if args.receiver else None));server.daemon_threads=True
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
        if recorder:recorder.close()
if __name__=='__main__':main()
