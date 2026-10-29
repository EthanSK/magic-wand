import unittest,json
from types import SimpleNamespace
from bridge import Store,Framer,validate,matching_port,ReceiverObserver,ActionControl,parse_action_post,ACTION_REQUEST
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
  _,a=self.actions({'pid':4242,'actionsPaused':True,'actionsPausedAt':12.5,'ready':True,'pointerPath':'direct'});self.assertEqual(a.state(),{'available':True,'paused':True,'since':12.5,'ready':True,'pointerPath':'direct'})
  _,a=self.actions({'pid':4242,'actionsPaused':False,'pointerPath':'smoothed'});self.assertIsNone(a.state()['pointerPath'],'unknown path is never shown as a real mode')
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
if __name__=='__main__':unittest.main()
