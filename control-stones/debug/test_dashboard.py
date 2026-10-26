"""Exercise the actual dashboard script without a browser, radio or pointer."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


class DashboardTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is required for dashboard checks")
    def test_all_sensors_stay_visible_and_fail_independently(self):
        html = Path(__file__).with_name("index.html").read_text()
        script = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
        harness = r"""
const vm = require('node:vm'), assert = require('node:assert/strict');
class Element {
  constructor(){ this.children=[]; this.fields=new Map(); this.dataset={}; this.value='';
    this.checked=false; this.textContent=''; this.classList={add(){},toggle(){},remove(){}}; }
  querySelector(key){ if(!this.fields.has(key)) this.fields.set(key,new Element()); return this.fields.get(key); }
  cloneNode(){ return new Element(); }
  append(node){ this.children.push(node); }
  setAttribute(){} addEventListener(){} setPointerCapture(){}
  getBoundingClientRect(){ return {width:200,height:36}; }
  getContext(){ return {scale(){},beginPath(){},moveTo(){},lineTo(){},stroke(){}}; }
}
const elements=new Map(), commands=[];
const get=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id)};
get('sensor-panel').content={firstElementChild:new Element()};
get('horizontal').value='gz';get('vertical').value='gx';get('gain').value='3';
const keys=['hand','finger:2','finger:3','finger:4','finger:5','finger:6'];
const sample={gx:1,gy:2,gz:3,ax:0,ay:0,az:1,ms:100};
let frame={sensors:Object.fromEntries(keys.map(key=>[key,{status:'Live',sample:{...sample},count:1,transport:'Bluetooth'}])),mouse:{available:true}};
let offline=false;
const context=vm.createContext({document:{getElementById:get,createElement:()=>new Element(),addEventListener(){}},
  window:{addEventListener(){}},devicePixelRatio:1,setTimeout(){},setInterval(){},clearInterval(){},
  fetch:async(url,options)=>{
    if(options?.method==='POST'){commands.push(JSON.parse(options.body));return {ok:true,json:async()=>({})};}
    if(offline)throw Error('offline');return {json:async()=>frame};
  }});
vm.runInContext(SCRIPT,context);
(async()=>{
  await new Promise(setImmediate);
  const cards=get('comparison').children;
  assert.deepEqual(cards.map(card=>card.dataset.sensor),keys);
  assert.equal(get('status').textContent,'All six sensors live');
  assert.equal(get('mouse-source').children.length,6);
  assert(!elements.has('source'),'The display must not depend on the old sensor selector');
  get('mouse-source').value='finger:6';
  await vm.runInContext('configure()',context);
  assert.equal(commands.at(-1).source,'finger:6');
  assert.equal(cards.length,6,'Mouse selection must not remove sensor cards');
  for(const sensor of Object.values(frame.sensors)) sensor.sample.idle=true;
  await vm.runInContext('poll()',context);
  assert(cards.every(card=>card.querySelector('[data-status]').textContent==='Bluetooth · Idle'));
  assert(cards.every(card=>card.querySelector('[data-hint]').textContent==='Gyro asleep; accelerometer watching for movement.'));
  for(const sensor of Object.values(frame.sensors)) sensor.sample.idle=false;
  frame.sensors['finger:4']={status:'No recent readings',sample:null};
  await vm.runInContext('poll()',context);
  assert.equal(get('status').textContent,'5 of 6 sensors live');
  assert.equal(cards[3].querySelector('[data-axis="gx"]').textContent,'—');
  assert.equal(cards[4].querySelector('[data-axis="gx"]').textContent,'1.00');
  offline=true;
  await vm.runInContext('poll()',context);
  assert.equal(get('status').textContent,'Debug reader unavailable');
  assert(cards.every(card=>card.querySelector('[data-axis="gx"]').textContent==='—'));
  assert.equal(get('hold').disabled,true);
})().catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run(
            [shutil.which("node"), "-"],
            input="const SCRIPT = " + json.dumps(script) + ";\n" + harness,
            text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
