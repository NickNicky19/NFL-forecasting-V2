/* Execute acquired consumer bytes without vendoring production code or outcomes. */
"use strict";
const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const [privateRoot,publicRoot]=process.argv.slice(2);if(!privateRoot||!publicRoot)throw Error("private input and public output directories required");
const read=n=>fs.readFileSync(path.join(privateRoot,n)),json=n=>JSON.parse(read(n)),hash=b=>crypto.createHash("sha256").update(b).digest("hex");
const save=(n,x)=>fs.writeFileSync(path.join(publicRoot,n),JSON.stringify(x,null,2)+"\n",{flag:"wx"});
async function main(){
 const started=Date.now(),acq=JSON.parse(fs.readFileSync(path.join(publicRoot,"FRESH_SERVED_ACQUISITION.json"))),protocol=JSON.parse(fs.readFileSync(path.join(publicRoot,"FROZEN_PROTOCOL.json")));
 const assets=Object.fromEntries(acq.receipts.map(r=>[r.kind,r]));
 for(const n of ["pointer.json","payload.json","consumer.js","app.js","board.json"])assert.equal(hash(read("fresh_"+n)),assets[n].sha256);
 const board=json("IDENTITY_ONLY_BOARD.json"),projection=JSON.parse(fs.readFileSync(path.join(publicRoot,"BOARD_METADATA_PROJECTION_RECEIPT.json")));
 assert.equal(hash(read("IDENTITY_ONLY_BOARD.json")),projection.projection_sha256);assert.equal(projection.NFL_statistic_scalars_decoded,0);
 const doc=json("fresh_payload.json"),pointer=json("fresh_pointer.json"),consumer=read("fresh_consumer.js").toString(),app=read("fresh_app.js").toString();
 const begin=app.indexOf("function selectedPropForecast("),end=app.indexOf("\nfunction propChip(",begin);assert(begin>=0&&end>begin);
 const slice=app.slice(begin,end),auditClock=Date.parse(acq.receipts.at(-1).receipt_completed_utc);
 save("RENDER_INPUT_BINDING.json",{state:"FROZEN_BEFORE_CONSUMER_EXECUTION",protocol_sha256:hash(fs.readFileSync(path.join(publicRoot,"FROZEN_PROTOCOL.json"))),acquisition_sha256:hash(fs.readFileSync(path.join(publicRoot,"FRESH_SERVED_ACQUISITION.json"))),board_metadata_projection_sha256:projection.projection_sha256,consumer_sha256:hash(Buffer.from(consumer)),app_sha256:hash(Buffer.from(app)),selected_function_slice_sha256:hash(Buffer.from(slice)),audit_helper_sha256:hash(fs.readFileSync(__filename)),audit_clock:new Date(auditClock).toISOString(),expected_count:1945,expected_new_mae_profile_rows:0,scope:"Exact acquired consumer.validate/card/load and extracted app selectedPropForecast. No complete app execution, raw board statistics, NFL outcomes, model inference or browser screenshot."});
 const context=vm.createContext({module:{exports:{}},S:{weeklyOverlay:null},crypto:crypto.webcrypto,AbortController,TextDecoder,TextEncoder,Uint8Array,setTimeout,clearTimeout});
 vm.runInContext(consumer,context,{timeout:1000});vm.runInContext(slice,context,{timeout:1000});const api=context.WeeklyAdaptiveOverlay;
 const overlay=api.validate(doc,board,assets["board.json"].sha256);assert.equal(overlay.rows.size,1945);context.S.weeklyOverlay=overlay;
 assert.equal(pointer.sha256,assets["payload.json"].sha256);assert.equal(pointer.bytes,assets["payload.json"].bytes);assert.equal(pointer.display_board_sha256,assets["board.json"].sha256);
 const players=new Map(board.players.map(p=>[JSON.stringify([p.game_id,p.id]),p]));const counts={},products={},methods={},issued={},persisted={},games={};let allValues=0,liveValues=0,exactCards=0,mae=0;
 const labels={point_mean:"mean",point_median:"median",binary_probability:"TD probability"};
 for(const row of doc.rows){
  const p=players.get(JSON.stringify([row.game_id,row.player_id]));assert(p);
  const probe=(Date.parse(row.first_prepared_at)+Date.parse(row.valid_until_utc))/2;
  const html=api.card(overlay,p,row.category,probe),r=context.selectedPropForecast(p,row.category,probe);assert(html&&r);assert.equal(r.value,row.forecast_value);assert.equal(r.label,labels[row.product]);
  const text=row.product==="binary_probability"?`${(100*row.forecast_value).toFixed(1)}%`:row.forecast_value.toFixed(2);assert.equal(r.text,text);assert(html.includes(text));allValues++;exactCards++;
  const card=api.card(overlay,p,row.category,auditClock),current=context.selectedPropForecast(p,row.category,auditClock);assert.equal(!!card,!!current);if(current){assert.equal(current.value,row.forecast_value);liveValues++;}
  const state=auditClock>=Date.parse(row.kickoff_utc)?(current?"frozen":"expired_after_kickoff"):(current?"future_renderable":"stale_before_kickoff");
  counts[row.category]??={rows:0,future_renderable:0,frozen:0,expired_after_kickoff:0,stale_before_kickoff:0,games:new Set()};counts[row.category].rows++;counts[row.category][state]++;counts[row.category].games.add(row.game_id);
  products[row.product]=(products[row.product]||0)+1;methods[row.method_id]=(methods[row.method_id]||0)+1;issued[row.issued_at]=(issued[row.issued_at]||0)+1;persisted[row.persistence_completed_at]=(persisted[row.persistence_completed_at]||0)+1;
  games[row.game_id]??={rows:0,kickoff:row.kickoff_utc,future_renderable:0,frozen:0,expired_after_kickoff:0,stale_before_kickoff:0};games[row.game_id].rows++;games[row.game_id][state]++;
  if(/stat_point_mae_v2/.test(row.method_id+row.procedure_version+row.model_version))mae++;
 }
 assert.equal(mae,0);assert.equal(allValues,1945);
 const clone=x=>JSON.parse(JSON.stringify(x)),tests=[];
 function rejects(name,mutate){const d=clone(doc);mutate(d);assert.throws(()=>api.validate(d,board,assets["board.json"].sha256));tests.push({name,status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});}
 const countCats=new Set(["pass_td","pass_cmp","pass_att","pass_int","rush_att","rec"]),countIndex=doc.rows.findIndex(r=>countCats.has(r.category));assert(countIndex>=0);
 rejects("count median is incompatible with served count mean wire contract",d=>{d.rows[countIndex].product="point_median";d.rows[countIndex].prediction_functional="intended_median";});
 rejects("extra expected_mean wire field is rejected",d=>{d.rows[countIndex].expected_mean=d.rows[countIndex].forecast_value;});
 rejects("post-cutoff persistence is rejected",d=>{d.rows[countIndex].persistence_completed_at=d.rows[countIndex].kickoff_utc;});
 assert.throws(()=>api.validate(doc,board,"0".repeat(64)));tests.push({name:"wrong display board hash rejected",status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});
 const p=players.get(JSON.stringify([doc.rows[countIndex].game_id,doc.rows[countIndex].player_id]));assert.equal(api.card(overlay,p,"unsupported_missing_category",auditClock),"");assert.equal(context.selectedPropForecast(p,"unsupported_missing_category",auditClock),null);tests.push({name:"missing selected row falls back",status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});
 const d=clone(doc),q=d.rows[countIndex],kickoff=Date.parse(q.kickoff_utc);q.valid_until_utc=new Date(kickoff-60000).toISOString();const stale=api.validate(d,board,assets["board.json"].sha256);context.S.weeklyOverlay=stale;assert.equal(api.card(stale,p,q.category,kickoff-30000),"");assert.equal(context.selectedPropForecast(p,q.category,kickoff-30000),null);assert.equal(api.card(stale,p,q.category,kickoff+1),"");tests.push({name:"expired early forecast disappears before and after kickoff",status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});
 q.valid_until_utc=q.kickoff_utc;const frozen=api.validate(d,board,assets["board.json"].sha256);context.S.weeklyOverlay=frozen;assert(api.card(frozen,p,q.category,kickoff+1).includes("Frozen provisional forecast"));assert.equal(context.selectedPropForecast(p,q.category,kickoff+1).frozen,true);tests.push({name:"valid through kickoff preserves frozen original value",status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});
 const rollback=clone(doc);rollback.state="DISABLED_USE_R0";rollback.rows=[];rollback.frozen_rows=[];const disabled=api.validate(rollback,board,assets["board.json"].sha256);context.S.weeklyOverlay=disabled;assert.equal(api.card(disabled,p,q.category,auditClock),"");assert.equal(context.selectedPropForecast(p,q.category,auditClock),null);tests.push({name:"disabled overlay rollback leaves no selected value",status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});
 const makeFetch=(mode)=>async url=>{
  if(mode==="missing")return new Response("missing",{status:404});
  const rel=String(url);if(rel==="data/weekly-adaptive-overlay.json")return new Response(read("fresh_pointer.json"));
  if(rel===pointer.path)return new Response(mode==="corrupt"?Buffer.from("{}"):read("fresh_payload.json"));
  return new Response("missing",{status:404});
 };
 const loaded=await api.load(board,assets["board.json"].sha256,makeFetch("normal"));assert.equal(loaded.rows.size,1945);tests.push({name:"actual pointer/payload load validates all acquired rows",status:"PASS",kind:"ACTUAL_SERVED_BYTES"});
 assert.equal(await api.load(board,assets["board.json"].sha256,makeFetch("missing")),null);tests.push({name:"missing optional asset returns normal fallback",status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});
 assert.equal(await api.load(board,assets["board.json"].sha256,makeFetch("corrupt")),null);tests.push({name:"payload hash mismatch returns normal fallback",status:"PASS",kind:"LABELLED_SOFTWARE_FIXTURE"});
 const categories=Object.fromEntries(Object.entries(counts).map(([k,v])=>[k,{...v,games:v.games.size}]));
 save("CONSUMER_EXECUTION_RESULT.json",{state:"PASS_ACTUAL_SERVED_CONSUMER_FUNCTION_PARITY",audit_clock:new Date(auditClock).toISOString(),consumer_sha256:assets["consumer.js"].sha256,app_sha256:assets["app.js"].sha256,payload_sha256:assets["payload.json"].sha256,display_board_sha256:assets["board.json"].sha256,season:doc.season,week:doc.week,registration_id:doc.registration_id,overlay_state:doc.state,payload_prepared_at:doc.prepared_at,payload_packaged_at:doc.packaged_at,rows:doc.rows.length,all_exact_valid_window_values_checked:allValues,all_exact_valid_window_cards_checked:exactCards,currently_renderable_values_checked:liveValues,stat_point_mae_v2_rows:mae,products,methods,categories,games,issued_at_counts:issued,persistence_completed_at_counts:persisted,declared_frozen_rows:doc.frozen_rows.length,fallback_counts:doc.fallback_counts,checks:tests,new_fits:0,new_inference:0,new_captures:0,new_grades:0,NFL_statistic_scalars_decoded:0,NFL_outcomes_used:0,wall_seconds:(Date.now()-started)/1000,max_RSS_bytes:process.resourceUsage().maxRSS*1024,scope_limit:"Function VM execution against actual acquired source and forecast bytes. No browser DOM/network rendering screenshot, new owner admission, forecast accuracy or target-game outcome verification."});
 console.log(JSON.stringify({state:"PASS",rows:allValues,currently_renderable:liveValues,mae_profile_rows:mae,categories,products,methods,tests:tests.length}));
}
main().catch(e=>{process.stderr.write(e.stack+"\n");process.exitCode=1;});
