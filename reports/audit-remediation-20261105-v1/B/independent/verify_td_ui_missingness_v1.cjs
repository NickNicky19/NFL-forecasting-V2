// Execute the pinned UI guard only; no browser, fetch, forecast or publication.
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const [appPath,boardPath,outPath]=process.argv.slice(2);
const app=fs.readFileSync(appPath,'utf8'),boardBytes=fs.readFileSync(boardPath);
const guard=app.match(/function baselineTdProbability\([^]*?\n\}/)?.[0];assert.ok(guard);
const ctx={};vm.createContext(ctx);vm.runInContext(guard,ctx);
const fixtures=[[{proj:null,td_chance:0},null],[{td_chance:0},null],[{proj:0,td_chance:0},0],[{proj:1,td_chance:.55},.55],[{proj:NaN,td_chance:0},null],[{proj:-1,td_chance:0},null]];
for(const [r,expected]of fixtures)assert.equal(ctx.baselineTdProbability(r),expected);
const b=JSON.parse(boardBytes),rows=b.players.flatMap(p=>p.props||[]).filter(p=>p.key==='anytime_td');
const missing=rows.filter(p=>p.proj==null),zeros=missing.filter(p=>p.td_chance===0);
assert.ok(zeros.every(p=>ctx.baselineTdProbability(p)===null));
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const result={state:'PASS_PINNED_CURRENT_UI_UNKNOWN_TD_GUARD',app_sha256:hash(Buffer.from(app)),board_sha256:hash(boardBytes),synthetic_cases:fixtures.length,board_generated_at:b.generated_at,anytime_td_rows:rows.length,missing_projection_rows:missing.length,missing_projection_serialized_zero_rows:zeros.length,false_display_zero_via_checked_guard:0,limits:['Actual guard executed, not browser rendering','Raw producer null-to-zero serialization remains a separate defect','Current board differs from audit November5 older snapshot; no overwrite or invented historical correction'],network_calls:0,source_edits:0};
fs.writeFileSync(outPath,JSON.stringify(result,null,2)+'\n',{flag:'wx'});process.stdout.write(JSON.stringify(result)+'\n');
