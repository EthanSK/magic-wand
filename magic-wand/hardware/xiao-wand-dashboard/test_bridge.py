import unittest,json
from types import SimpleNamespace
from bridge import Store,Framer,validate,matching_port,ReceiverObserver

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
if __name__=='__main__':unittest.main()
