// B independent, synthetic-only fixture of exact existing website functions.
// No website write, model inference, selector replay, offer, or NFL grade.
const fs = require('node:fs');
const crypto = require('node:crypto');
const vm = require('node:vm');
const path = require('node:path');

const sourcePath = process.argv[2];
if (!sourcePath) throw Error('Supply already-read immutable app.js bytes');
const source = fs.readFileSync(sourcePath, 'utf8');
const sha = x => crypto.createHash('sha256').update(x).digest('hex');
const expected = '8aa97d75b8a444e4711e972535211208f8ee72414ad48b8840a17075c8a5b52f';
if (sha(source) !== expected) throw Error('Source changed; inspect rather than guess');
const names = ['isClassicBaseline', 'selectedRankingPolicy', 'baselineTdProbability', 'effectivePropForecast', 'selectedPropGap'];
const snippets = names.map(name => {
  const start = source.indexOf('function ' + name + '(');
  const end = source.indexOf('\n}', start) + 2;
  if (start < 0 || end < start) throw Error('Exact function not found');
  return {name, code: source.slice(start, end)};
});
const context = vm.createContext({
  S: {data: {execution_model: {model: 'sleeper-matchup-classic-presence-strict-v2'}}, lines: {}},
  // The current inspected overlay is disabled. This is the real numeric
  // baseline branch. Candidate feed validation/admission is NOT mocked/passed.
  selectedPropForecast: () => null,
});
vm.runInContext(snippets.map(x => x.code).join('\n') + '\nthis.checkedGap=selectedPropGap;', context);
const player = {id: 'SYNTHETIC_ONLY', reference_model: 'sleeper-matchup-classic-presence-strict-v2'};
const cases = [
  {id: 'CMP_NEAR_LINE', key: 'pass_cmp', point: 22.7, line: 22.5, expectedStrict: 'Over', expectedLean: null},
  {id: 'CMP_OUTSIDE_MARGIN', key: 'pass_cmp', point: 23.5, line: 22.5, expectedStrict: 'Over', expectedLean: 'over'},
  {id: 'CMP_EQUAL', key: 'pass_cmp', point: 22.5, line: 22.5, expectedStrict: 'ABSTAIN', expectedLean: null},
  {id: 'YARDS_EXACT_MARGIN', key: 'pass_yd', point: 258.5, line: 250.5, expectedStrict: 'Over', expectedLean: null},
  {id: 'ZERO_RECEPTION_POINT', key: 'rec', point: 0, line: .5, expectedStrict: 'Under', expectedLean: 'under'},
  {id: 'NULL_POINT', key: 'pass_cmp', point: null, line: 22.5, expectedStrict: null, expectedLean: null},
  {id: 'MISSING_LINE', key: 'pass_cmp', point: 22.7, line: null, expectedStrict: null, expectedLean: null},
  {id: 'INTERNAL_REFERENCE_SOURCE', key: 'pass_cmp', point: 23.5, line: 22.5, lineFrom: 'ours', expectedStrict: 'Over', expectedLean: null},
  {id: 'CUSTOM_CHANGED_LINE', key: 'pass_cmp', point: 22.7, line: 22.5, changedLine: 24.5, expectedStrict: 'Under', expectedLean: 'under'},
];
const rows = cases.map(c => {
  context.S.lines = c.changedLine === undefined ? {} : {[player.id + '|' + c.key]: c.changedLine};
  const effectiveLine = c.changedLine === undefined ? c.line : c.changedLine;
  const strict = typeof c.point === 'number' && Number.isFinite(c.point) && typeof effectiveLine === 'number' && Number.isFinite(effectiveLine)
    ? c.point > effectiveLine ? 'Over' : c.point < effectiveLine ? 'Under' : 'ABSTAIN' : null;
  const result = context.checkedGap(player, {key: c.key, adj: c.point, line: c.line, line_from: c.lineFrom || 'dk'}, c.changedLine !== undefined);
  const lean = result ? result.lean : null;
  if (strict !== c.expectedStrict || lean !== c.expectedLean) throw Error('Fixture mismatch: ' + c.id);
  return {...c, strictP1: strict, consumerLean: lean, consumerGap: result ? result.gap : null, consumerSource: result ? result.source : null};
});
const output = {
  id: 'B-ACTUAL-CONSUMER-GAP-FIXTURE-v1', executed_UTC: new Date().toISOString(),
  source: {repository: 'NickNicky19/nicks-expert-nfl-picks', commit: 'ccfaa987f5416ca6abce2570f9fee8c4c41c1d3e', path: 'output/app.js', sha256: sha(source)},
  exact_extracted_functions: snippets.map(x => ({name: x.name, sha256: sha(x.code)})),
  node: process.version, status: 'PASS_ALL9_SYNTHETIC_CASES', cases: rows,
  scope: 'Exact selectedPropGap + real numeric fallback functions; no current feed validator/DOM/producer/model/Top Picks replay exercised. selectedPropForecast dependency is null, matching observed disabled overlay.',
  conclusion: 'Strict P1 crossing and existing margin-based category lean are different complete decision policies. A P1 release needs a separately versioned strict category consumer or five-week evaluation of the actual margin policy; it cannot borrow P1 accuracy unchanged.',
  zero_note: 'Zero is a valid numeric point here. The separate Top Picks ratio/minimum-line gates are not exercised or changed by this fixture.',
  custom_line_note: 'Changed displayed line recomputes direction; it is not an original saved selection or registered repricing decision.',
  new_fits: 0, new_NFL_observations: 0, new_offers: 0, new_selections: 0, new_grades: 0, website_writes: 0,
};
const target = path.join(__dirname, 'ACTUAL_CONSUMER_RULE_FIXTURE_V1.json');
fs.writeFileSync(target, JSON.stringify(output, null, 2) + '\n', {flag: 'wx'});
console.log(JSON.stringify({status: output.status, source_sha256: sha(source), fixtures: rows.length}));
