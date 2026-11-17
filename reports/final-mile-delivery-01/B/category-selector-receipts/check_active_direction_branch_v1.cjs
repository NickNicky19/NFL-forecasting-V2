/* Four synthetic branch checks against the pinned real propChip function.
 * Helpers are declared stubs; this proves source selection, not a browser run,
 * complete inference, selectedPropGap arithmetic or new NFL observations.
 */
const fs = require('fs');
const crypto = require('crypto');
const vm = require('vm');
const [sourcePath, outputPath] = process.argv.slice(2);
const source = fs.readFileSync(sourcePath, 'utf8');
const sha = x => crypto.createHash('sha256').update(x).digest('hex');
if (sha(source) !== '8aa97d75b8a444e4711e972535211208f8ee72414ad48b8840a17075c8a5b52f') throw Error('Changed source');
const start = source.indexOf('function propChip(');
const end = source.indexOf('\nfunction catCard(', start);
if (start < 0 || end < start) throw Error('Missing real function boundary');
const functionSource = source.slice(start, end);
let chosen = null, display = null, gapCalls = 0;
const context = { S: { lines: {}, data: {} }, pv: (_p, r) => r,
  baselineTdProbability: () => null,
  selectedPropForecast: () => chosen, maeDisplayForecast: () => display,
  selectedPropGap: () => { gapCalls++; return { lean: 'under' }; },
  propStatus: () => null, SHORT: { pass_cmp: 'CMP' }, LINE_TAG: { dk: 'DK' },
  esc: x => x, fmtStat: (_k, x) => String(x), isClassicBaseline: () => true };
vm.runInNewContext(functionSource + '\nthis.invoke = propChip;', context);
const raw = { key: 'pass_cmp', adj: 22.7, line: 22.5, line_from: 'dk', lean: 'over' };
const results = [];
function test(name, lean, selected, mae, expectedLean, expectedCalls) {
  gapCalls = 0; chosen = selected; display = mae;
  const html = context.invoke({ id: 'SYNTHETIC' }, { ...raw, lean });
  const actual = html.includes('lean-under') ? 'under' : html.includes('lean-over') ? 'over' : null;
  if (actual !== expectedLean || gapCalls !== expectedCalls) throw Error(name + ' failed');
  results.push({ name, raw_serialized_lean: lean, selected: Boolean(selected), mae_display: Boolean(mae),
    rendered_class_lean: actual, selected_gap_calls: gapCalls, expected: expectedLean, PASS: true });
}
test('BASELINE_SERIALIZED_OVER_PRESERVED', 'over', null, null, 'over', 0);
test('BASELINE_NULL_PRESERVED', null, null, null, null, 0);
test('SELECTED_OVERRIDE_USES_SELECTED_GAP', 'over', { text: '25.5', label: 'SYNTHETIC' }, null, 'under', 1);
test('DISPLAY_ONLY_MAE_PRESERVES_BASELINE_LEAN', 'over', null, { text: '28', label: 'SYNTHETIC' }, 'over', 0);
if (fs.existsSync(outputPath)) throw Error('Frozen output exists');
fs.writeFileSync(outputPath, JSON.stringify({ id: 'B-FINALMILE-ACTIVE-DIRECTION-BRANCH-v1',
  actual_UTC: new Date().toISOString(), source_path: 'output/app.js', source_ref: '869d9a8839ae83dfccdb3bbb6610a0e0df867667',
  source_sha256: sha(source), extracted_function_sha256: sha(functionSource), checks: results,
  conclusion: 'Baseline propChip uses serialized prop.lean; selectedPropGap controls selected override. A separate MAE display does not change baseline ranking lean.',
  scope: 'Real function with declared helper stubs and synthetic inputs; no full DOM/browser, inference, probability, grade or live activation claim.',
  new_NFL_observations: 0, new_fits: 0 }, null, 2) + '\n');
