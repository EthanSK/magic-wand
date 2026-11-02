// Regenerate the mathematical report from its prose template and canonical
// inputs. Run node make-report.mjs, then render-study.py, then --record.
// --check is read-only and rejects stale inputs, prose, calculations or figures.
import {readFileSync,writeFileSync} from 'node:fs';
import {dirname,resolve,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {study} from './mechanics-study.mjs';
const here=dirname(fileURLToPath(import.meta.url));
const args=process.argv.slice(2);
const mode=args.find(v=>v.startsWith('--'));
if(mode && !['--check','--record'].includes(mode)) throw new Error('Use --check or --record');
if(args.filter(v=>v.startsWith('--')).length>1) throw new Error('Choose one mode');
const roots=args.filter(v=>!v.startsWith('--'));
if(roots.length>1) throw new Error('Pass at most one repository root');
const repo=resolve(roots[0]??resolve(here,'../../../..'));
const r=await study(repo);
const s=r.inputs.scenario;
const row=values=>'| '+values.join(' | ')+' |';
const percent=v=>(v*100).toFixed(2)+'%';
const replacements={
  PREFERRED_LENGTH_CM:r.preferred_prototype.brief.preferred_overall_length_mm/10,
  PREFERRED_LENGTH_MM:r.preferred_prototype.brief.preferred_overall_length_mm,
  NEAR_GRIP_MASS:s.near_grip_package_g,
  SCENARIO_TIP_MASS:s.tip_package_g,
  TIP_LEVER_CM:(s.baseline_length_mm-s.grip_from_butt_mm)/10,
  TIP_PER_GRAM_INERTIA:(0.001*((s.baseline_length_mm-s.grip_from_butt_mm)/1000)**2).toPrecision(7),
  SELECTED_PLACEMENT_IMAGE:relative(here,resolve(repo,r.preferred_prototype.brief.cad_reference.placement_image)),
  REFERENCE_STATUS:r.preferred_prototype.reference_matches_selected_length
    ? 'The referenced CAD currently matches that overall length, but fit and physical acceptance remain unverified.'
    : `The referenced CAD still shows ${r.preferred_prototype.placement.overall_length/10} cm overall; it is an earlier reference, not the selected size, while the fit review progresses.`,
  CAD_OVERALL_MM:r.preferred_prototype.placement.overall_length.toFixed(2),
  CAD_TUBE_MM:r.preferred_prototype.placement.rod_length.toFixed(2),
  CAD_KEY_EDGE_MM:r.preferred_prototype.placement.lower_cap_edge_from_butt_mm.toFixed(2),
  CAD_KEY_MOVE_MM:r.preferred_prototype.placement.carrier_move_from_existing_layout_mm?.toFixed(2)??'0.00',
  PCB_CENTRE_MM:r.preferred_prototype.pcb_reference_centre_from_butt_mm.toFixed(2),
  PIVOT_HYPOTHESES:r.preferred_prototype.sensitivity_inputs.pivot_hypotheses_from_butt_mm.join(', '),
  SELECTED_INERTIA_RANGE:[Math.min(...r.preferred_prototype.cases.map(v=>v.inertia_fraction_of_500mm_tube)),
    Math.max(...r.preferred_prototype.cases.map(v=>v.inertia_fraction_of_500mm_tube))].map(percent).join('–'),
  LAYOUT_TABLE:r.preferred_prototype.cases.map(v=>row([`${v.pivot_hypothesis_mm} mm`,
    v.tip_point_hypothesis==='tube_end'?'Tube end':'PCB geometric centre',
    percent(v.inertia_fraction_of_500mm_tube),`${v.gravity_moment_N_m.toFixed(5)} Nm`])).join('\n'),
  WIRE_TABLE:r.preferred_prototype.cases.filter(v=>v.tip_point_hypothesis==='pcb_geometric_center')
    .map(v=>row([`${v.pivot_hypothesis_mm} mm`,v.per_gram_wire.inertia_kg_m2.toExponential(3)+' kg m²',
      v.per_gram_wire.gravity_moment_N_m.toFixed(6)+' Nm'])).join('\n'),
  INPUTS:`density ${s.density_g_cm3} g/cm³; tip ${s.tip_package_g} g; near-grip package ${s.near_grip_package_g} g; grip ${s.grip_from_butt_mm/10} cm from butt`,
  SAME_TABLE:r.same_packages.map(v=>row([`${v.length_mm/10} cm`,`${v.total_g.toFixed(2)} g`,`${v.torque_N_m.toFixed(5)} Nm`,percent(v.inertia_fraction)])).join('\n'),
  MASS_SAVING:(r.baseline.total_g-r.same_packages.find(v=>v.length_mm===350).total_g).toFixed(2),
  HOLDER_MASS:r.related_supplier_sensitivity.holder_slicer_g.toFixed(3),
  RELATED_TIP:r.related_supplier_sensitivity.package_reference_before_extra_leads_g.toFixed(3),
  RELATED_BOARD_MASS:r.related_supplier_sensitivity.source.value_g,
  RELATED_BOARD_SKU:r.related_supplier_sensitivity.source.sku,
  RELATED_BOARD_SOURCE:r.related_supplier_sensitivity.source.source,
  RELATED_BOARD_IDENTITY_SOURCE:r.related_supplier_sensitivity.source.identity_source,
  RELATED_BOARD_PDF:r.related_supplier_sensitivity.source.manufacturer_pdf,
  HALF_LENGTH:(r.explicit_half_grip_moment_target.length_mm/10).toFixed(2),
  HALF_INERTIA:percent(r.explicit_half_grip_moment_target.inertia_fraction),
  HALF_RANGE:[r.explicit_half_grip_moment_target.source_input_endpoint_range_mm[0],r.explicit_half_grip_moment_target.source_input_endpoint_range_mm.at(-1)].map(v=>(v/10).toFixed(2)).join('–'),
  RELATED_HALF_LENGTH:(r.related_supplier_sensitivity.half_grip_moment_target.length_mm/10).toFixed(2),
  CURRENT_COM:(r.baseline.centre_from_butt_mm/10).toFixed(2),
  MOVING_GRIP_COM:(r.pivot_to_balance_tube_and_tip_mm/10).toFixed(2),
  CW_TABLE:r.balance_by_butt_counterweight.map(v=>row([`${v.length_mm/10} cm`,`${v.counterweight_at_butt_g.toFixed(2)} g`,`${v.balanced_total_g.toFixed(2)} g`,v.balanced_inertia_kg_m2.toFixed(7)])).join('\n'),
  ISO_TABLE:r.constant_inertia_counterexample.map(v=>row([`${v.length_mm/10} cm`,`${v.tip_g.toFixed(2)} g`,`${(v.tube_g+v.tip_g).toFixed(2)} g`,`${v.total_g.toFixed(2)} g`,`${v.torque_N_m.toFixed(5)} Nm`])).join('\n'),
  RANGE_TABLE:r.same_packages.map((v,i)=>row([`${v.length_mm/10} cm`,`${percent(v.exact_ratio_envelope.minimum.ratio)}–${percent(v.exact_ratio_envelope.maximum.ratio)}`,`${percent(r.arbitrary_tube_tip_mass_ratio_bounds[i].minimum)}–${percent(r.arbitrary_tube_tip_mass_ratio_bounds[i].maximum)}`])).join('\n'),
  TARGET_TABLE:r.conditional_inertia_targets.map(v=>row([percent(v.inertia_fraction),`${(v.length_mm/10).toFixed(2)} cm`])).join('\n'),
};
let report=readFileSync(resolve(here,'report-source.md'),'utf8');
report=report.replace(/\{\{([A-Z_]+)\}\}/g,(_,key)=>{
  if(!(key in replacements)) throw new Error(`Unknown report token ${key}`);
  return replacements[key];
});
const expected={
  'results.json':JSON.stringify(r,null,2)+'\n',
  'REPORT.md':'<!-- Generated by make-report.mjs; edit report-source.md and canonical inputs. -->\n\n'+report,
};
const hash=path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const localHash=name=>hash(resolve(here,name));
const manifest=JSON.parse(readFileSync(resolve(here,'../manifest.json'),'utf8'));
const holder=manifest.profiles['r2-three-key'].components.find(c=>c.id==='sensor_holder').mass_ref.path;
const inputs=[resolve(here,'../manifest.json'),resolve(here,'../derive.mjs'),
  resolve(repo,manifest.scenarios['illustrative-lengths'].tube_parameters),resolve(repo,holder),
  ...['parameters','manifest','assembly','placement_image','render_receipt'].map(key=>resolve(repo,manifest.prototype_briefs['physical-v3'].cad_reference[key])),
  ...['mechanics-study.mjs','make-report.mjs','report-source.md','render-study.py','renderer-requirements.txt'].map(name=>resolve(here,name))];
const inputHashes=()=>Object.fromEntries(inputs.map(path=>[relative(repo,path),hash(path)]));
const outputs=['results.json','REPORT.md','geometry-and-comparison.png','mechanical-pareto.png','figures-provenance.json'];
if(!mode) {
  for(const [name,content] of Object.entries(expected)) writeFileSync(resolve(here,name),content);
  console.log(`Generated report; ${r.illustrative_candidates.length} illustrative candidate rows, ${r.finite_candidate_frontier.length} nondominated rows. Render figures, then use --record.`);
} else {
  for(const [name,content] of Object.entries(expected)) {
    if(readFileSync(resolve(here,name),'utf8')!==content) throw new Error(`Stale ${name}; regenerate the report and figures`);
  }
  const figures=JSON.parse(readFileSync(resolve(here,'figures-provenance.json'),'utf8'));
  for(const [name,expectedHash] of Object.entries({...figures.inputs,...figures.outputs})) {
    if(localHash(name)!==expectedHash) throw new Error(`Stale figure dependency or output: ${name}`);
  }
  const provenance={schema_version:1,inputs:inputHashes(),outputs:Object.fromEntries(outputs.map(name=>[name,localHash(name)]))};
  if(mode==='--record') {
    writeFileSync(resolve(here,'provenance.json'),JSON.stringify(provenance,null,2)+'\n');
    console.log('Recorded report and figure provenance');
  } else {
    const previous=JSON.parse(readFileSync(resolve(here,'provenance.json'),'utf8'));
    if(JSON.stringify(previous)!==JSON.stringify(provenance)) throw new Error('Stale report provenance; regenerate and record');
    console.log('Report, calculations, figures and input provenance are current');
  }
}
