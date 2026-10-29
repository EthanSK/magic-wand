import * as THREE from '../../../../../docs/lib/three-0.185.1/three.module.min.js';
import {ViewInput,frameBounds} from '../../preview/view-input.mjs';
const stage=document.querySelector('#stage'),scene=new THREE.Scene();scene.background=new THREE.Color('#e4ebef');
const camera=new THREE.PerspectiveCamera(34,1,.1,5000),renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));stage.prepend(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff,0x8294a0,2.5));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(-180,500,260);scene.add(light);
const input=new ViewInput({fov:34,minDistance:30,maxDistance:3500}),group=new THREE.Group();scene.add(group);let view='assembled';
const manifest=await fetch('../exports/manifest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Model unavailable');return r.json()});
function clear(){for(const x of [...group.children]){group.remove(x);x.geometry?.dispose();x.material?.dispose()}}
function rebuild(){clear();for(const [i,p]of manifest.parts.entries()){
const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p.assembly_vertices.flat(),3));g.setIndex(p.assembly_faces.flat());g.rotateX(-Math.PI/2);g.computeVertexNormals();const m=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:[0x218b9e,0x2597a9,0x2ca3b4][i],roughness:.42,metalness:.12}));if(view==='parts'){g.computeBoundingBox();m.position.x=(i-1)*42;m.position.y=-g.boundingBox.min.y;}group.add(m)}
if(view!=='parts'){const pts=[];for(let z=10;z<473;z+=3){const radius=(8-2.2*Math.min(z,460)/460)/2+1.2;pts.push(new THREE.Vector3(radius, z, -.8))}const wire=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:0xd07a30}));group.add(wire)}
document.querySelector('#status').hidden=true;home()}
function home(){const box=new THREE.Box3().setFromObject(group);if(view==='head'){box.min.set(-18,430,-18);box.max.set(18,503,18)}input.setHome(frameBounds(box.min.toArray(),box.max.toArray(),{aspect:stage.clientWidth/stage.clientHeight,fov:34,yaw:.48,pitch:.08,padding:1.12}));render()}
function render(){const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();camera.position.fromArray(input.camera());camera.lookAt(...input.target);renderer.render(scene,camera)}
for(const b of document.querySelectorAll('[data-mode]'))b.onclick=()=>{input.setMode(b.dataset.mode);for(const x of document.querySelectorAll('[data-mode]'))x.classList.toggle('on',x===b)};
document.querySelector('#view').onchange=e=>{view=e.target.value;rebuild()};document.querySelector('#reset').onclick=home;document.querySelector('#in').onclick=()=>{input.zoomSteps(1);render()};document.querySelector('#out').onclick=()=>{input.zoomSteps(-1);render()};
renderer.domElement.onpointerdown=e=>{stage.focus();input.pointerDown(e.pointerId,e.clientX,e.clientY);renderer.domElement.setPointerCapture(e.pointerId)};
renderer.domElement.onpointermove=e=>{if(input.pointerMove(e.pointerId,e.clientX,e.clientY,stage.clientHeight))render()};for(const n of ['pointerup','pointercancel','lostpointercapture'])renderer.domElement.addEventListener(n,e=>input.pointerUp(e.pointerId));
renderer.domElement.onwheel=e=>{e.preventDefault();if(input.wheel(e,stage.clientHeight))render()};stage.onkeydown=e=>{if(input.key(e,stage.clientHeight)){e.preventDefault();render()}};window.addEventListener('blur',()=>input.cancel());window.onresize=home;rebuild();
