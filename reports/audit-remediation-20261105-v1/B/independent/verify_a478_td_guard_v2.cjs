// Actual pinned UI guard only. No old board is represented as current.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const [sourcePath,outputPath]=process.argv.slice(2),source=fs.readFileSync(sourcePath,'utf8');
const guard=source.match(/function baselineTdProbability\([^]*?\n\}/)?.[0];assert.ok(guard);
const context={};vm.createContext(context);vm.runInContext(guard,context);
const cases=[[{proj:null,td_chance:null},null],[{proj:null,td_chance:0},null],[{td_chance:0},null],[{proj:0,td_chance:0},0],[{proj:1,td_chance:.55},.55],[{proj:NaN,td_chance:0},null],[{proj:-1,td_chance:0},null],[{proj:1,td_chance:1.1},null],[{proj:1,td_chance:NaN},null]];
for(const [value,expected]of cases)assert.equal(context.baselineTdProbability(value),expected);
const result={state:'PASS_PINNED_A478_ACTUAL_UI_TD_GUARD',production_commit:'a478db86e2702d9fa632a23bfaf9c575a67ea902',app_sha256:crypto.createHash('sha256').update(source).digest('hex'),synthetic_guard_cases:cases.length,current_board_evaluated:false,browser_render_claim:false,network_calls:0,source_edits:0,limits:'Immutable code pin only; concurrent later owner code/capture is separate. Unknown serialization guard passes; no claim of NFL probability calibration or historical grading corrections.'};
fs.writeFileSync(outputPath,JSON.stringify(result,null,2)+'\n',{flag:'wx'});process.stdout.write(JSON.stringify(result)+'\n');
