import json,os,tempfile,unittest
from pathlib import Path
from bridge import RollingReadings,Store,accepted_usage
from measure import read_rows,pointer_use_rows
from test_bridge import packet

def usage(posts=0,travel=0,paused=False):
 return dict(pointerPosts=posts,pointerTravel=travel,paused=paused,follow=True,recording=False,hud=False,pointerPath='direct')
class RecordingsTests(unittest.TestCase):
 def test_recording_is_automatic_private_bounded_and_strips_untrusted_fields(self):
  with tempfile.TemporaryDirectory() as directory:
   recorder=RollingReadings(directory,max_bytes=2048,backups=2)
   store=Store(recorder=recorder);session=store.begin('Bluetooth')
   for seq in range(1,31):
    p=packet(seq);p['device_identifier']='private-do-not-keep'
    p.update(imuFlags=3,sampleCount=1,firstMicros=seq*20000)
    store.record(p,'Bluetooth',session,{**usage(seq,seq*2),'windowTitle':'never-keep'})
   recorder.queue.join()
   self.assertEqual(store.snapshot()['capture'],dict(enabled=True,dropped=0,error=False))
   recorder.close();files=list(Path(directory).glob('readings.jsonl*'))
   self.assertLessEqual(len(files),3)
   for file in files:self.assertEqual(file.stat().st_mode&0o777,0o600)
   rows=read_rows(directory);self.assertTrue(rows)
   self.assertEqual(rows[-1]['usage']['pointerTravel'],60)
   self.assertEqual(rows[-1]['packet']['sampleCount'],1)
   self.assertEqual(rows[-1]['age_ms'],0)
   self.assertNotIn('private-do-not-keep',json.dumps(rows));self.assertNotIn('windowTitle',json.dumps(rows))
 def test_active_windows_need_posted_travel_not_sensor_motion_or_follow(self):
  def row(i,u,session=1):return dict(id=i,session=session,transport='Bluetooth',packet=packet(i),poll=float(i),usage=u)
  rows=[row(1,usage()),row(2,usage()),row(3,usage(1,3)),row(4,usage(1,3)),row(5,usage(2,8,True)),row(6,usage(3,10)),row(7,usage(4,12))]
  self.assertEqual([r['id'] for r in pointer_use_rows(rows)],[2,3,6,7])
  self.assertEqual(pointer_use_rows([row(1,usage(10,50)),row(2,usage(1,2),2)]),[])
  self.assertEqual(pointer_use_rows([{'packet':packet(1)}]),[])
  self.assertIsNone(accepted_usage({**usage(),'pointerTravel':float('nan')}))
  self.assertIsNone(accepted_usage({**usage(),'paused':1}))
 def test_recording_loader_accepts_only_a_truncated_last_line(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'readings.jsonl';path.write_text('{"packet":{}}\n{')
   self.assertEqual(read_rows(path),[{'packet':{}}])
   path.write_text('{\n{"packet":{}}\n')
   with self.assertRaises(ValueError):read_rows(path)
if __name__=='__main__':unittest.main()
