// Independent identities, integration and extremum checks for the private
// mathematical study. Run node --test mechanics-study.test.mjs.
import test from 'node:test';
import assert from 'node:assert/strict';
import {inertiaSI,firstMomentSI,derivativesSI,ratioEnvelope,nondominated,lengthForMomentRatio,componentLayoutSI} from './mechanics-study.mjs';

const close=(a,b,tolerance=1e-10)=>assert.ok(Math.abs(a-b)<=tolerance,`${a} != ${b}`);
const lambda=0.01884955592153876, L=0.5,p=0.09,m=0.004,a=0.0000070625;

test('limiting cases give a rod at its end, rod at centre, and a point mass',()=>{
  close(inertiaSI(lambda,L,0,0),lambda*L**3/3);
  close(inertiaSI(lambda,L,L/2,0),lambda*L**3/12);
  close(inertiaSI(0,L,p,m),m*(L-p)**2);
});

test('closed form agrees with independent midpoint integration',()=>{
  const count=100000,dy=L/count;
  let integrated=0;
  for(let i=0;i<count;i++) integrated+=lambda*dy*(((i+0.5)*dy-p)**2+a);
  integrated+=m*(L-p)**2;
  close(integrated,inertiaSI(lambda,L,p,m,a),1e-12);
});

test('length and pivot derivatives agree with central differences',()=>{
  const h=1e-6,d=derivativesSI(lambda,L,p,m,a);
  close((inertiaSI(lambda,L+h,p,m,a)-inertiaSI(lambda,L-h,p,m,a))/(2*h),d.inertia_wrt_length_kg_m,1e-10);
  close((inertiaSI(lambda,L,p+h,m,a)-inertiaSI(lambda,L,p-h,m,a))/(2*h),d.inertia_wrt_pivot_kg_m,1e-10);
  close(d.inertia_wrt_pivot_kg_m,-2*firstMomentSI(lambda,L,p,m));
});

test('inertia-ratio extrema bound a dense two-dimensional sweep',()=>{
  for(const shorter of [0.35,0.30,0.25,0.20]) {
    const envelope=ratioEnvelope(lambda,[shorter,L],[0.08,0.10],[0.0025,0.0055],a);
    for(let i=0;i<=200;i++) for(let j=0;j<=100;j++) {
      const pivot=0.08+0.02*i/200,tip=0.0025+0.003*j/100;
      const ratio=inertiaSI(lambda,shorter,pivot,tip,a)/inertiaSI(lambda,L,pivot,tip,a);
      assert.ok(ratio>=envelope.minimum.ratio-1e-12&&ratio<=envelope.maximum.ratio+1e-12);
    }
  }
});

test('balanced two-endpoint distribution attains the mass-inertia bound',()=>{
  const back=0.09,front=0.41,frontMass=0.010,backMass=frontMass*front/back;
  const total=frontMass+backMass,I=frontMass*front**2+backMass*back**2;
  close(frontMass*front-backMass*back,0);
  close(I,total*back*front);
  // For every interior point x: x² <= (b-a)x+ab.
  for(let i=0;i<=100;i++) {
    const x=-back+(front+back)*i/100;
    assert.ok(x*x<=(front-back)*x+back*front+1e-15);
  }
});

test('finite Pareto selector removes only dominated candidates',()=>{
  const good={total_g:10,torque_N_m:0.01,length_mm:300,inertia_kg_m2:0.001};
  const bad={total_g:11,torque_N_m:0.02,length_mm:350,inertia_kg_m2:0.0009};
  const tradeoff={total_g:12,torque_N_m:0.01,length_mm:300,inertia_kg_m2:0.0012};
  assert.deepEqual(nondominated([good,bad,tradeoff]),[good,tradeoff]);
});

test('conditional half-moment length satisfies the stated target and is maximal',()=>{
  const target=firstMomentSI(lambda,L,p,m)/2;
  const solved=lengthForMomentRatio(lambda,L,p,m,0.5);
  close(firstMomentSI(lambda,solved,p,m),target,1e-14);
  assert.ok(firstMomentSI(lambda,solved+0.0001,p,m)>target);
  assert.ok(firstMomentSI(lambda,solved-0.0001,p,m)<target);
  close(lengthForMomentRatio(0,L,p,m,0.5),(L+p)/2);
});

test('distributed wire and off-tip package agree with independent integration',()=>{
  const input={lambda:0.02,length:0.3,pivot:0.13,tipY:0.2884,tipMass:0.004,
    nearY:0.10875,nearMass:0.017,wireMass:0.001,radialA:a};
  const result=componentLayoutSI(input);let q=0,I=0;const n=100000;
  for(let i=0;i<n;i++) {
    const tubeY=(i+.5)*input.length/n,dm=input.lambda*input.length/n;
    q+=dm*(tubeY-input.pivot);I+=dm*((tubeY-input.pivot)**2+a);
    const wireY=input.nearY+(i+.5)*(input.tipY-input.nearY)/n,wm=input.wireMass/n;
    q+=wm*(wireY-input.pivot);I+=wm*(wireY-input.pivot)**2;
  }
  for(const [mass,y] of [[input.tipMass,input.tipY],[input.nearMass,input.nearY]]) {
    q+=mass*(y-input.pivot);I+=mass*(y-input.pivot)**2;
  }
  close(q,result.first_moment_kg_m,1e-12);close(I,result.inertia_kg_m2,1e-12);
});
