// Derive the wand's conditional mechanical trade-offs from the canonical
// blueprint scenario. Run node mechanics-study.mjs /path/to/magic-wand.
// This reads sources and writes JSON to stdout; it never builds CAD or changes hardware.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const G = 9.80665;
const readJSON = path => JSON.parse(readFileSync(path, 'utf8'));

// The reference exporter bakes coordinates into untransformed, root-level
// meshes. Refuse a different layout instead of mistaking local bounds for world bounds.
function referenceBounds(path, name) {
  const bytes=readFileSync(path);
  if(bytes.toString('ascii',0,4)!=='glTF'||bytes.readUInt32LE(4)!==2) throw new Error('Expected GLB2');
  const doc=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)).toString());
  const index=doc.nodes.findIndex(node=>node.name===name),node=doc.nodes[index];
  if(!node||node.matrix||node.translation||node.rotation||node.scale
    ||!doc.scenes[doc.scene??0].nodes.includes(index)) throw new Error(`Unrecognised reference transform: ${name}`);
  const bounds=doc.meshes[node.mesh].primitives.map(p=>doc.accessors[p.attributes.POSITION]);
  if(bounds.some(b=>!b.min||!b.max)) throw new Error(`Missing reference bounds: ${name}`);
  return [0,1,2].map(axis=>[Math.min(...bounds.map(b=>b.min[axis])),Math.max(...bounds.map(b=>b.max[axis]))]);
}

/** Collinear tube, two point packages and a uniform wire segment, all in SI. */
export function componentLayoutSI({lambda,length,pivot,tipY,tipMass,nearY,nearMass,wireMass=0,radialA=0}) {
  const centreWire=(nearY+tipY)/2,span=tipY-nearY;
  const mass=lambda*length+tipMass+nearMass+wireMass;
  const moment=lambda*(length*length/2-pivot*length)+tipMass*(tipY-pivot)
    +nearMass*(nearY-pivot)+wireMass*(centreWire-pivot);
  const inertia=lambda*(((length-pivot)**3+pivot**3)/3+length*radialA)
    +tipMass*(tipY-pivot)**2+nearMass*(nearY-pivot)**2
    +wireMass*((centreWire-pivot)**2+span*span/12);
  return {mass_kg:mass,first_moment_kg_m:moment,inertia_kg_m2:inertia,gravity_moment_N_m:moment*G};
}

/** SI line-model inertia; the radial term belongs to the hollow tube only. */
export function inertiaSI(lambda, length, pivot, tipMass, radialA = 0) {
  return lambda * (((length - pivot) ** 3 + pivot ** 3) / 3 + length * radialA)
    + tipMass * (length - pivot) ** 2;
}

export function firstMomentSI(lambda, length, pivot, tipMass) {
  return lambda * (length ** 2 / 2 - pivot * length) + tipMass * (length - pivot);
}

export function derivativesSI(lambda, length, pivot, tipMass, radialA = 0) {
  const x = length - pivot;
  return {
    mass_wrt_length_kg_per_m: lambda,
    moment_wrt_length_kg: lambda * x + tipMass,
    inertia_wrt_length_kg_m: lambda * (x * x + radialA) + 2 * tipMass * x,
    inertia_wrt_pivot_kg_m: -2 * firstMomentSI(lambda, length, pivot, tipMass),
    inertia_wrt_tip_mass_m2: x * x,
    moment_wrt_tip_mass_m: x,
  };
}

/** Largest length (least shortening) meeting a chosen fraction of forward
 * grip moment, for fixed masses and pivot. The target is a design choice. */
export function lengthForMomentRatio(lambda, baselineLength, pivot, tipMass, ratio) {
  const target=firstMomentSI(lambda,baselineLength,pivot,tipMass)*ratio;
  if(lambda===0) return pivot+target/tipMass;
  const b=tipMass-lambda*pivot,c=-tipMass*pivot-target;
  return (-b+Math.sqrt(b*b-2*lambda*c))/lambda;
}

/** Exact extrema in pivot for a ratio of quadratic inertias. Tip-mass
 * dependence is fractional-linear, so the mass endpoints suffice. */
export function ratioEnvelope(lambda, lengths, pivots, tipMasses, radialA = 0) {
  const [length, baselineLength] = lengths;
  const rows = [];
  const coefficients = (l, m) => [lambda * l + m, -lambda * l * l - 2 * m * l,
    lambda * l ** 3 / 3 + lambda * l * radialA + m * l * l];
  for (const mass of tipMasses) {
    const [a,b,c] = coefficients(length, mass);
    const [d,e,f] = coefficients(baselineLength, mass);
    const qa = a*e-b*d, qb = 2*(a*f-c*d), qc = b*f-c*e;
    const candidates = [...pivots];
    if (Math.abs(qa) < 1e-20) {
      if (Math.abs(qb) > 1e-20) candidates.push(-qc/qb);
    } else {
      const discriminant = qb*qb-4*qa*qc;
      if (discriminant >= 0) {
        const root = Math.sqrt(discriminant);
        candidates.push((-qb-root)/(2*qa),(-qb+root)/(2*qa));
      }
    }
    for (const pivot of candidates.filter(p => p >= pivots[0] && p <= pivots[1])) {
      rows.push({ pivot_m:pivot, tip_mass_kg:mass,
        ratio:inertiaSI(lambda,length,pivot,mass,radialA)
          / inertiaSI(lambda,baselineLength,pivot,mass,radialA) });
    }
  }
  rows.sort((a,b) => a.ratio-b.ratio);
  return { minimum:rows[0], maximum:rows.at(-1), candidates_checked:rows.length };
}

/** A finite candidate set is illustrative, never a global optimum proof. */
export function nondominated(rows) {
  const scores = row => [row.total_g, Math.abs(row.torque_N_m), row.length_mm, -row.inertia_kg_m2];
  const dominates = (a,b) => a.every((v,i) => v <= b[i] + 1e-12)
    && a.some((v,i) => v < b[i] - 1e-12);
  return rows.filter(b => !rows.some(a => a !== b && dominates(scores(a),scores(b))));
}

export async function study(repo) {
  const dir=resolve(repo,'magic-wand/hardware/assembly-blueprint');
  const manifest=readJSON(resolve(dir,'manifest.json'));
  const scenario=manifest.scenarios['illustrative-lengths'];
  const params=readJSON(resolve(repo,scenario.tube_parameters));
  const { lengthCase }=await import(pathToFileURL(resolve(dir,'derive.mjs')).href);
  const outer=params.rod.diameter, inner=params.rod.inside_diameter;
  const rho=scenario.density_g_cm3, p=scenario.grip_from_butt_mm;
  const tip=scenario.tip_package_g, grip=scenario.near_grip_package_g;
  const area=Math.PI*((outer/2000)**2-(inner/2000)**2);
  const lambda=rho*1000*area;
  const radialA=((outer/2000)**2+(inner/2000)**2)/4;
  const brief=manifest.prototype_briefs['physical-v3'];
  const preferredManifest=readJSON(resolve(repo,brief.cad_reference.manifest));
  const placement=preferredManifest.assembly_reference;
  const glbHash=createHash('sha256').update(readFileSync(resolve(repo,brief.cad_reference.assembly))).digest('hex');
  if(glbHash!==preferredManifest.assembly_glb_sha256) throw new Error('Preferred CAD GLB does not match its manifest');
  const renderReceipt=readJSON(resolve(repo,brief.cad_reference.render_receipt));
  const hash=path=>createHash('sha256').update(readFileSync(resolve(repo,path))).digest('hex');
  if(hash(brief.cad_reference.manifest)!==renderReceipt.manifest_sha256
    ||hash(brief.cad_reference.placement_image)!==renderReceipt.placement_image_sha256) {
    throw new Error('Preferred CAD placement image does not match its source receipt');
  }
  const bakedBounds=referenceBounds(resolve(repo,brief.cad_reference.assembly),'REFERENCE_pcb');
  const pcbBounds=placement.pcb_reference_bounds_mm;
  const pcbCentre=placement.pcb_reference_center_from_butt_mm;
  if(!pcbBounds||!Number.isFinite(pcbCentre)) throw new Error('Preferred CAD is missing PCB reference metadata');
  for(let axis=0;axis<3;axis++) for(let end=0;end<2;end++) {
    if(Math.abs(pcbBounds[end][axis]-bakedBounds[axis][end])>0.0001) throw new Error('Preferred CAD PCB bounds disagree with GLB');
  }
  const geometrySensitivity=manifest.scenarios['preferred-geometry-sensitivity'];
  const preferredCases=[];
  for(const pivotMM of geometrySensitivity.pivot_hypotheses_from_butt_mm) {
    for(const point of geometrySensitivity.tip_point_hypotheses) {
      const tipMM=point==='tube_end'?placement.tube_tip_reference_y_mm:pcbCentre;
      const offsetMM=placement.tube_tip_reference_y_mm-tipMM;
      const common={lambda,pivot:pivotMM/1000,tipMass:tip/1000,
        nearY:placement.carrier_local_origin_from_butt_mm/1000,nearMass:grip/1000,radialA};
      const current=componentLayoutSI({...common,length:placement.rod_length/1000,tipY:tipMM/1000});
      const comparison=componentLayoutSI({...common,length:0.5,tipY:(500-offsetMM)/1000});
      const withWire=componentLayoutSI({...common,length:placement.rod_length/1000,tipY:tipMM/1000,
        wireMass:geometrySensitivity.wire_addition_g/1000});
      preferredCases.push({pivot_hypothesis_mm:pivotMM,tip_point_hypothesis:point,tip_point_mm:tipMM,
        ...current,inertia_fraction_of_500mm_tube:current.inertia_kg_m2/comparison.inertia_kg_m2,
        per_gram_wire:{mass_g:geometrySensitivity.wire_addition_g,
          inertia_kg_m2:withWire.inertia_kg_m2-current.inertia_kg_m2,
          gravity_moment_N_m:withWire.gravity_moment_N_m-current.gravity_moment_N_m}});
    }
  }
  const lengths=[scenario.baseline_length_mm,...scenario.candidate_lengths_mm];
  const base=(length,pivot=p,tipMass=tip) => {
    const r=lengthCase(outer,inner,length,rho,tipMass,grip,pivot);
    return { length_mm:length, pivot_mm:pivot, tip_g:tipMass,
      tube_g:r.tube_mass_g, total_g:r.total_g,
      inertia_kg_m2:r.inertia_about_grip_x_g_mm2*1e-9,
      torque_N_m:r.horizontal_gravity_torque_N_m,
      centre_from_butt_mm:r.centre_of_mass_mm[1] };
  };
  const baseline=base(lengths[0]);
  const relatedSource=manifest.products.sensor_board.supplier_related_mass_reference;
  const holderReference=manifest.profiles['r2-three-key'].components.find(c=>c.id==='sensor_holder').mass_ref;
  const holderReceipt=readJSON(resolve(repo,holderReference.path));
  const holderMass=holderReference.pointer.split('/').slice(1).reduce((v,k)=>v[k],holderReceipt);
  const relatedTip=relatedSource.value_g+holderMass;
  const relatedHalf=lengthForMomentRatio(lambda,lengths[0]/1000,p/1000,relatedTip/1000,0.5)*1000;
  const halfMomentLength=lengthForMomentRatio(lambda,lengths[0]/1000,p/1000,tip/1000,0.5)*1000;
  const halfMomentCase=base(halfMomentLength);
  const samePackages=lengths.map(length => ({ ...base(length),
    inertia_fraction:base(length).inertia_kg_m2/baseline.inertia_kg_m2,
    exact_ratio_envelope:ratioEnvelope(lambda,[length/1000,lengths[0]/1000],
      scenario.range_inputs.grip_from_butt_mm.map(v=>v/1000),
      scenario.range_inputs.tip_package_g.map(v=>v/1000),radialA) }));
  const arbitraryMassRatioBounds=lengths.map(length=>{
    const pivotBounds=scenario.range_inputs.grip_from_butt_mm.map(v=>v/1000);
    const tube=ratioEnvelope(1,[length/1000,lengths[0]/1000],pivotBounds,[0],radialA);
    const tipOnly=ratioEnvelope(0,[length/1000,lengths[0]/1000],pivotBounds,[1],0);
    return {length_mm:length,minimum:Math.min(tube.minimum.ratio,tipOnly.minimum.ratio),
      maximum:Math.max(tube.maximum.ratio,tipOnly.maximum.ratio),
      scope:'Any nonnegative uniform-tube/point-tip mass ratio; excludes finite grip/component intrinsic inertia'};
  });
  const constantInertia=lengths.map(length => {
    const tubeI=base(length,p,0).inertia_kg_m2;
    const x=(length-p)/1000;
    const neededTip=(baseline.inertia_kg_m2-tubeI)/(x*x)*1000;
    return { ...base(length,p,neededTip), added_tip_ballast_g:neededTip-tip,
      scope:'Counterexample only: artificial same-inertia constraint, not the design objective' };
  });
  const counterweights=lengths.map(length => {
    const r=base(length);
    const counterweight=r.torque_N_m/G/(p/1000)*1000;
    return { ...r, counterweight_at_butt_g:counterweight,
      balanced_total_g:r.total_g+counterweight,
      balanced_inertia_kg_m2:r.inertia_kg_m2+counterweight/1000*(p/1000)**2,
      balanced_torque_N_m:0 };
  });
  const perGramRelocation=lengths.map(length => ({length_mm:length,
    from_tip_to_grip_torque_reduction_N_m:G*0.001*(length-p)/1000,
    from_tip_to_grip_inertia_reduction_kg_m2:0.001*((length-p)/1000)**2,
    from_tip_to_grip_total_mass_change_g:0,
    scope:'Per gram moved; this is not a claim about board or battery mass' }));
  const inertiaTargets=[0.10,0.25,0.50,0.75,1].map(fraction=>{
    let low=p,high=lengths[0];
    for(let i=0;i<70;i++) {
      const middle=(low+high)/2;
      if(base(middle).inertia_kg_m2<baseline.inertia_kg_m2*fraction) low=middle;
      else high=middle;
    }
    return {...base((low+high)/2),inertia_fraction:fraction,
      scope:'Conditional inversion only: the chosen inertia fraction is not a measured steadiness requirement'};
  });
  const candidates=[];
  for (const length of lengths) for (const pivot of scenario.range_inputs.grip_from_butt_mm) {
    const original=base(length,pivot);
    for (const tipOffsetFraction of [0,0.5,1]) {
      const y=pivot+(length-pivot)*tipOffsetFraction;
      const moved={...original,
        tip_position_mm:y,
        centre_from_butt_mm:original.centre_from_butt_mm+tip*(y-length)/original.total_g,
        inertia_kg_m2:original.inertia_kg_m2+tip/1000*(((y-pivot)/1000)**2-((length-pivot)/1000)**2),
        torque_N_m:original.torque_N_m+G*tip/1000*(y-length)/1000 };
      const balanceMass=moved.torque_N_m/G/(pivot/1000)*1000;
      for (const fraction of [0,0.5,1]) {
        if (balanceMass<0 && fraction>0) continue;
        const added=balanceMass*fraction;
        candidates.push({...moved, counterweight_g:added,
          total_g:moved.total_g+added,
          centre_from_butt_mm:moved.total_g*moved.centre_from_butt_mm/(moved.total_g+added),
          torque_N_m:moved.torque_N_m-G*added/1000*pivot/1000,
          inertia_kg_m2:moved.inertia_kg_m2+added/1000*(pivot/1000)**2});
      }
    }
  }
  return { scope:'Assumed scenario, not a fitted-wand optimum or a prediction of steadiness',
    inputs:{scenario,outer_mm:outer,inner_mm:inner,lambda_kg_per_m:lambda,radial_a_m2:radialA},
    preferred_prototype:{brief,placement,pcb_reference_bounds_mm:pcbBounds,pcb_reference_centre_from_butt_mm:pcbCentre,
      reference_matches_selected_length:placement.overall_length===brief.preferred_overall_length_mm,
      sensitivity_inputs:geometrySensitivity,cases:preferredCases,
      scope:'CAD-reference sensitivity only; numerical axes are not measured pivots and PCB centre is not package COM. No wiring mass has been assigned to the physical wand.'},
    baseline,same_packages:samePackages,arbitrary_tube_tip_mass_ratio_bounds:arbitraryMassRatioBounds,
    related_supplier_sensitivity:{source:relatedSource,holder_slicer_g:holderMass,
      package_reference_before_extra_leads_g:relatedTip,baseline:base(lengths[0],p,relatedTip),
      half_grip_moment_target:base(relatedHalf,p,relatedTip),
      limit:'Related-SKU catalogue reference plus sliced plastic, not measured fitted tip mass or a guaranteed lower bound'},
    explicit_half_grip_moment_target:{...halfMomentCase,
      inertia_fraction:halfMomentCase.inertia_kg_m2/baseline.inertia_kg_m2,
      target_is:'Agent-chosen experimental priority, not a measured or universal optimum',
      source_input_endpoint_range_mm:scenario.range_inputs.grip_from_butt_mm.flatMap(pivot=>
        scenario.range_inputs.tip_package_g.map(tipMass=>lengthForMomentRatio(lambda,
          lengths[0]/1000,pivot/1000,tipMass/1000,0.5)*1000)).sort((a,b)=>a-b)},
    constant_inertia_counterexample:constantInertia,
    conditional_inertia_targets:inertiaTargets,
    balance_by_butt_counterweight:counterweights,per_gram_relocation:perGramRelocation,
    pivot_to_balance_tube_and_tip_mm:(lambda*(lengths[0]/1000)**2/2+tip/1000*lengths[0]/1000)
      /(lambda*lengths[0]/1000+tip/1000)*1000,
    axial_ideal_minimum_balanced_mass_for_baseline_inertia_g:baseline.inertia_kg_m2
      /((p/1000)*((lengths[0]-p)/1000))*1000,
    illustrative_candidates:candidates,
    finite_candidate_frontier:nondominated(candidates),
    frontier_scope:'Only this sampled finite set under min mass, min absolute static torque, min length, max transverse inertia. Inertia is not measured steadiness. No battery mass has been invented.' };
}

if (process.argv[1] && resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  if (!process.argv[2]) throw new Error('Pass the repository root');
  console.log(JSON.stringify(await study(resolve(process.argv[2])),null,2));
}
