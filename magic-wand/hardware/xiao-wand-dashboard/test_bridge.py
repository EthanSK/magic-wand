import unittest,json
from types import SimpleNamespace
from bridge import Store,Framer,validate,matching_port,ReceiverObserver,ActionControl,parse_action_post,ACTION_REQUEST,parse_input_report,ReceiverInputs
import calendar
import os,tempfile
from pathlib import Path

def packet(seq=1):return {'schema':1,'sensor':'wand','seq':seq,'ms':seq*20,'buttons':dict(thumb=False,index=False,middle=False),'imu':dict(ax=0,ay=0,az=1,gx=0,gy=0,gz=0)}
class BridgeTests(unittest.TestCase):
 def test_fresh_and_stale_are_distinct(self):
  now=[0.0];s=Store(lambda:now[0]);n=s.begin('USB');s.record(packet(),'USB',n);self.assertEqual(s.snapshot()['status'],'live');now[0]=1.5;self.assertEqual(s.snapshot()['status'],'stale')
 def test_usb_blocks_wireless_and_old_session(self):
  s=Store();n=s.begin('Bluetooth');s.usb_present=True;self.assertFalse(s.record(packet(),'Bluetooth',n));m=s.begin('USB');self.assertFalse(s.record(packet(),'USB',n));self.assertTrue(s.record(packet(),'USB',m))
 def test_cursor_returns_only_new_frames_and_never_identifiers(self):
  s=Store();n=s.begin('USB');p=packet();p['device_identifier']='not public';s.record(p,'USB',n);self.assertNotIn('device_identifier',json.dumps(s.snapshot()));self.assertEqual(len(s.snapshot(1)['packets']),0);s.record(packet(2),'USB',n);self.assertEqual(len(s.snapshot(1)['packets']),1)
 def test_framing_recovers(self):
  out=[];f=Framer(out.append);v=(json.dumps(packet())+'\n').encode();f.feed(v[:25]);f.feed(v[25:]);f.feed(b'x'*3000+b'\n'+v);self.assertEqual(len(out),2)
 def test_button_packet_is_required(self):
  p=packet();p['sensor']='hand'
  with self.assertRaises(ValueError):validate(p)
  p=packet();p['buttons']['thumb']=0
  with self.assertRaises(ValueError):validate(p)
  p=packet();p['schema']=True
  with self.assertRaises(ValueError):validate(p)
 def test_match_original_sense_but_not_unrelated_board(self):
  for pid in [0x8045,0x0045]:self.assertTrue(matching_port(SimpleNamespace(vid=0x2886,pid=pid,product='XIAO nRF52840 Sense')))
  self.assertFalse(matching_port(SimpleNamespace(vid=0x2886,pid=0x9999,product='XIAO MG24')))
 def test_receiver_observer_reads_owner_packets_without_hardware(self):
  # No socket is bound here: only the datagram handling is exercised.
  s=Store();o=object.__new__(ReceiverObserver);o.store=s;o.sessions={}
  o.receive(json.dumps({'type':'packet','transport':'USB','session':3,'packet':packet(1)}).encode())
  o.receive(json.dumps({'type':'packet','transport':'USB','session':3,'packet':packet(2)}).encode())
  snap=s.snapshot(0);self.assertEqual(snap['status'],'live');self.assertEqual(snap['transport'],'USB');self.assertEqual(len(snap['packets']),2)
  o.receive(json.dumps({'type':'packet','transport':'Bluetooth','session':4,'packet':packet(1)}).encode())
  self.assertEqual(s.snapshot()['transport'],'Bluetooth');self.assertEqual(s.snapshot()['session'],2,'a receiver session change is a new dashboard session')
  o.receive(b'not json');o.receive(json.dumps({'type':'packet','transport':'Serial','session':5,'packet':packet(9)}).encode())
  bad=packet(10);bad['sensor']='hand';o.receive(json.dumps({'type':'packet','transport':'Bluetooth','session':4,'packet':bad}).encode())
  self.assertEqual(s.cursor,3)
  o.receive(json.dumps({'type':'status','state':'searching','session':4}).encode());self.assertEqual(s.status,'searching')
 def test_restarted_receiver_session_number_is_a_new_browser_sequence(self):
  s=Store();o=object.__new__(ReceiverObserver);o.store=s;o.sessions={}
  def receive(v):o.receive(json.dumps(v).encode())
  receive({'type':'packet','transport':'USB','session':1,'packet':packet(900)})
  old=s.session
  receive({'type':'status','state':'live','transport':'USB','session':1})
  receive({'type':'packet','transport':'USB','session':1,'packet':packet(1)})
  self.assertGreater(s.session,old);self.assertEqual(s.snapshot()['packets'][0]['packet']['seq'],1)
  self.assertTrue(s.usb_present)
 # Debug pause: the receiver owns the state; this page only requests and displays it.
 def actions(self,status=None,alive=lambda pid:pid==4242,receiver=None):
  d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);root=Path(d.name)
  if status is not None:(root/'status.json').write_text(json.dumps(status))
  t=[0.0]
  def sleep(dt):
   t[0]+=dt
   if receiver:receiver(root)
  return root,ActionControl(root,alive=alive,clock=lambda:t[0],sleep=sleep)
 def test_actions_unavailable_without_a_live_current_receiver(self):
  for status,alive in [(None,lambda pid:True),({'pid':4242,'actionsPaused':True},lambda pid:False),({'pid':4242},lambda pid:True),({'pid':'4242','actionsPaused':False},lambda pid:True)]:
   _,a=self.actions(status,alive);self.assertEqual(a.state(),{'available':False,'paused':None},status)
  _,a=self.actions({'pid':4242,'actionsPaused':True,'actionsPausedAt':12.5,'ready':True,'pointerPath':'direct'});self.assertEqual(a.state(),{'available':True,'paused':True,'since':12.5,'ready':True,'pointerPath':'direct','connected':False,'battery':None})
  _,a=self.actions({'pid':4242,'actionsPaused':False,'pointerPath':'smoothed'});self.assertIsNone(a.state()['pointerPath'],'unknown path is never shown as a real mode')
 def test_battery_is_the_receivers_voltage_estimate_with_its_age_only(self):
  root,a=self.actions({'pid':4242,'actionsPaused':False,'connected':True,'battery':{'percent':81,'volts':3.987,'measuredAt':1000}})
  a.wall=lambda:1090
  self.assertEqual(a.state()['battery'],{'percent':81,'volts':3.99,'ageSeconds':90});self.assertTrue(a.state()['connected'])
  for bad in [{'percent':81.5,'volts':3.9,'measuredAt':1},{'percent':120,'volts':3.9,'measuredAt':1},{'percent':50,'volts':9,'measuredAt':1},'81%',None]:
   _,b=self.actions({'pid':4242,'actionsPaused':False,'battery':bad});self.assertIsNone(b.state()['battery'],bad)
  self.assertNotIn('hours',json.dumps(a.state()),'no runtime is invented')
 def test_actions_request_waits_for_the_receivers_acknowledgement(self):
  def receiver(root):
   request=root/ACTION_REQUEST
   if not request.exists():return
   self.assertEqual(os.stat(request).st_mode&0o777,0o600)
   value=json.loads(request.read_text());request.unlink()
   self.assertEqual(set(value),{'version','paused','id'})
   (root/'status.json').write_text(json.dumps({'pid':4242,'actionsPaused':value['paused'],'actionsRequest':value['id'],'actionsPausedAt':99}))
  root,a=self.actions({'pid':4242,'actionsPaused':False},receiver=receiver)
  code,value=a.request(True);self.assertEqual((code,value['paused'],value['confirmed']),(200,True,True))
  code,value=a.request(False);self.assertEqual((code,value['paused'],value['confirmed'],value['since']),(200,False,True,None))
  self.assertEqual([p.name for p in root.iterdir()],['status.json'],'no request or temporary file left behind')
 def test_actions_request_never_claims_success_or_leaves_a_late_request(self):
  root,a=self.actions({'pid':4242,'actionsPaused':False})
  code,value=a.request(True);self.assertEqual((code,value['paused'],value['confirmed']),(504,False,False))
  self.assertFalse((root/ACTION_REQUEST).exists())
  _,gone=self.actions({'pid':4242,'actionsPaused':False},alive=lambda pid:False)
  self.assertEqual(gone.request(True),(503,{'available':False,'paused':None,'confirmed':False}))
 def test_action_post_is_same_origin_json_with_one_boolean(self):
  ok={'Host':'127.0.0.1:8872','Origin':'http://127.0.0.1:8872','Content-Type':'application/json','Sec-Fetch-Site':'same-origin'}
  self.assertEqual(parse_action_post(ok,b'{"paused":true}',8872),(200,True))
  self.assertEqual(parse_action_post({**ok,'Host':'localhost:8872','Origin':'http://localhost:8872'},b'{"paused":false}',8872),(200,False))
  self.assertEqual(parse_action_post({**ok,'Origin':'http://localhost:8872'},b'{"paused":true}',8872),(403,'origin'))
  for headers,body,code in [({**ok,'Host':'evil:8872'},b'{"paused":true}',403),({k:v for k,v in ok.items() if k!='Origin'},b'{"paused":true}',403),
     ({**ok,'Origin':'http://evil.example'},b'{"paused":true}',403),({**ok,'Sec-Fetch-Site':'cross-site'},b'{"paused":true}',403),
     ({**ok,'Content-Type':'text/plain'},b'{"paused":true}',415),(ok,None,413),(ok,b'x'*65,413),(ok,b'nope',400),
     (ok,b'{"paused":1}',400),(ok,b'{"paused":true,"code":"x"}',400),(ok,b'[true]',400)]:
   self.assertEqual(parse_action_post(headers,body,8872)[0],code,(headers,body))
 # Firmware 14 pin reports, read from Wand Receiver's log (no hardware, no socket).
 def test_pin_report_lines_parse_only_when_complete(self):
  levels,at=parse_input_report('2026-11-23T03:00:44Z SENSE_EVENT in D0=1:0 D1=1:52 D4=0:80 D6=1:178 D8=0:178\n')
  self.assertEqual(levels,{'D0':{'level':1,'changes':0},'D1':{'level':1,'changes':52},'D4':{'level':0,'changes':80},'D6':{'level':1,'changes':178},'D8':{'level':0,'changes':178}})
  self.assertEqual(at,calendar.timegm((2026,11,23,3,0,44,0,0,0)),'log times are UTC')
  for bad in ['2026-11-23T03:00:44Z SENSE_EVENT in D6=2:1','2026-11-23T03:00:44Z SENSE_EVENT in D6=1:1 D6=0:2','x 2026-11-23T03:00:44Z SENSE_EVENT in D6=1:1',
              '2026-11-23T03:00:44Z SENSE_EVENT in D6=1:1 other','2026-11-23T03:00:44Z SENSE_EVENT in ','2026-11-23T03:00:44Z SENSE_UPDATE busy','2026-13-45T03:00:44Z SENSE_EVENT in D6=1:1']:
   self.assertIsNone(parse_input_report(bad),bad)
 def test_pin_reports_have_their_own_bounded_cursor(self):
  now=[10.0];s=Store(lambda:now[0])
  self.assertEqual(s.snapshot()['inputs'],{'cursor':0,'age_ms':None,'rows':[]})
  for i in range(300):s.record_inputs({'D6':{'level':i%2,'changes':i}})
  now[0]=10.5;snap=s.snapshot(-1,-1)['inputs']
  self.assertEqual(snap['cursor'],300);self.assertEqual([r['id'] for r in snap['rows']],[300],'a new page gets only the latest report');self.assertEqual(snap['age_ms'],500)
  self.assertEqual(len(s.snapshot(-1,0)['inputs']['rows']),256);self.assertEqual([r['id'] for r in s.snapshot(-1,298)['inputs']['rows']],[299,300])
  self.assertEqual(s.snapshot(-1,-1)['cursor'],0,'pin reports never move the packet cursor')
 def test_receiver_log_reader_follows_appends_and_replacement(self):
  with tempfile.TemporaryDirectory() as d:
   log=Path(d)/'receiver.log';logged=calendar.timegm((2026,11,23,3,0,44,0,0,0))
   log.write_text('2026-11-23T03:00:43Z SENSE_EVENT in D6=0:0 D8=1:0\n2026-11-23T03:00:44Z SENSE_EVENT in D6=1:1 D8=0:1\nother line\n')
   s=Store();r=object.__new__(ReceiverInputs);r.path=log;r.store=s;r.clock=lambda:100.0;r.wall=lambda:logged+2;r.file=None;r.inode=None;r.partial=''
   r.step();self.assertEqual(s.input_cursor,1,'only the latest earlier report is shown');self.assertEqual(s.inputs[-1]['received'],98.0,'placed at its log time')
   with log.open('a') as f:f.write('2026-11-23T03:00:45Z SENSE_EVENT in D6=0:2 D8=1:2\n2026-11-23T03:00:45Z SENSE_EVENT in D6=1:3')
   r.step();self.assertEqual(s.input_cursor,2,'a line still being written waits')
   with log.open('a') as f:f.write(' D8=0:3\n')
   r.step();self.assertEqual(s.input_cursor,3);self.assertEqual(s.inputs[-1]['levels'],{'D6':{'level':1,'changes':3},'D8':{'level':0,'changes':3}})
   new=Path(d)/'new.log';new.write_text('2026-11-23T03:01:00Z SENSE_EVENT in D6=1:0\n');os.replace(new,log)
   r.step();r.step();self.assertEqual(s.input_cursor,4,'a replaced log is read from its start')
   log.write_text('');r.step();log.write_text('2026-11-23T03:01:01Z SENSE_EVENT in D6=0:1\n');r.step();r.step();self.assertEqual(s.input_cursor,5,'a truncated log is reopened')
   link=Path(d)/'link.log';link.symlink_to(log);q=object.__new__(ReceiverInputs);q.path=link;q.store=s;q.clock=lambda:0;q.wall=lambda:0;q.file=None;q.inode=None;q.partial=''
   self.assertRaises(OSError,q.step);r.file.close()
if __name__=='__main__':unittest.main()
