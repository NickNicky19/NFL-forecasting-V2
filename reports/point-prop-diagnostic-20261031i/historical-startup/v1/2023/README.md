# 2023: startup versus later regular-season numerical forecasts

This is a new split of already completed historical forecasts: Weeks1–4versus5–18, all twelve targets,457exact procedure/history/output/policy cells. No model was fitted or invoked and no full-season score was rerun. The fixed Leaf-CDF exemplar below makes category coverage readable; every procedure, loss and own learned/fallback split remains in the canonical source.

| Category | CURRENT W1–4 | RECENT W1–4 | MULTI W1–4 | CURRENT W5–18 | RECENT W5–18 | MULTI W5–18 | Strict-current early / later |
|---|---|---|---|---|---|---|---|
| anytime_td | 0.191971; n=1178; fallback=629/1196 | 0.141097; n=1178; fallback=126/1196 | 0.141097; n=1178; fallback=126/1196 | 0.144745; n=3884; fallback=49/3942 | 0.143479; n=3884; fallback=49/3942 | 0.143479; n=3884; fallback=49/3942 | 0.194199 / 0.146285 |
| nick-chart-ppr-v1 | 6.535245; n=1325; fallback=706/1348 | 4.796196; n=1325; fallback=137/1348 | 4.796196; n=1325; fallback=137/1348 | 4.404417; n=4388; fallback=63/4453 | 4.375811; n=4388; fallback=63/4453 | 4.375811; n=4388; fallback=63/4453 | 6.941540 / 4.480492 |
| pass_att | 21.407895; n=152; fallback=115/152 | 9.730263; n=152; fallback=10/152 | 9.730263; n=152; fallback=10/152 | 8.657534; n=511; fallback=14/511 | 8.338552; n=511; fallback=14/511 | 8.338552; n=511; fallback=14/511 | 21.065789 / 8.749511 |
| pass_cmp | 14.131579; n=152; fallback=115/152 | 6.901316; n=152; fallback=10/152 | 6.901316; n=152; fallback=10/152 | 5.937378; n=511; fallback=14/511 | 5.675147; n=511; fallback=14/511 | 5.675147; n=511; fallback=14/511 | 13.947368 / 6.093933 |
| pass_int | 0.631579; n=152; fallback=115/152 | 0.703947; n=152; fallback=10/152 | 0.703947; n=152; fallback=10/152 | 0.663405; n=511; fallback=14/511 | 0.688845; n=511; fallback=14/511 | 0.688845; n=511; fallback=14/511 | 0.631579 / 0.694716 |
| pass_td | 1.052632; n=152; fallback=115/152 | 0.736842; n=152; fallback=10/152 | 0.736842; n=152; fallback=10/152 | 0.812133; n=511; fallback=14/511 | 0.808219; n=511; fallback=14/511 | 0.808219; n=511; fallback=14/511 | 1.052632 / 0.802348 |
| pass_yd | 144.342105; n=152; fallback=115/152 | 74.302632; n=152; fallback=10/152 | 74.302632; n=152; fallback=10/152 | 74.023483; n=511; fallback=14/511 | 70.287671; n=511; fallback=14/511 | 70.287671; n=511; fallback=14/511 | 144.625000 / 76.729941 |
| rec | 1.936333; n=1178; fallback=629/1196 | 1.440577; n=1178; fallback=126/1196 | 1.440577; n=1178; fallback=126/1196 | 1.243048; n=3884; fallback=49/3942 | 1.233007; n=3884; fallback=49/3942 | 1.233007; n=3884; fallback=49/3942 | 2.033107 / 1.271627 |
| rec_yd | 21.723260; n=1178; fallback=629/1196 | 17.467742; n=1178; fallback=126/1196 | 17.467742; n=1178; fallback=126/1196 | 16.524974; n=3884; fallback=49/3942 | 16.505407; n=3884; fallback=49/3942 | 16.505407; n=3884; fallback=49/3942 | 23.360781 / 17.047889 |
| rush_att | 5.064516; n=496; fallback=258/497 | 3.316532; n=496; fallback=45/497 | 3.316532; n=496; fallback=45/497 | 3.064299; n=1633; fallback=27/1640 | 3.049602; n=1633; fallback=27/1640 | 3.049602; n=1633; fallback=27/1640 | 5.524194 / 3.133497 |
| rush_rec_yd | 29.162988; n=1178; fallback=629/1196 | 22.201188; n=1178; fallback=126/1196 | 22.201188; n=1178; fallback=126/1196 | 20.799176; n=3884; fallback=49/3942 | 20.706231; n=3884; fallback=49/3942 | 20.706231; n=3884; fallback=49/3942 | 31.387097 / 21.119979 |
| rush_yd | 22.633065; n=496; fallback=258/497 | 17.350806; n=496; fallback=45/497 | 17.350806; n=496; fallback=45/497 | 16.848745; n=1633; fallback=27/1640 | 16.774648; n=1633; fallback=27/1640 | 16.774648; n=1633; fallback=27/1640 | 24.729839 / 17.301898 |

Cells show native MAE, except anytime-TD uses Brier, followed by supported n and issued fallback/forecast counts. Do not compare unlike native units across categories. Nick chart remains the qualified partial-label research contract, not unrestricted full rare-component completeness or website-fantasy parity. The exact Leaf procedure/version, full empirical-median/event reference, membership match, error change and nonzero-denominator skill are in[the machine table](LEAF_STARTUP_COMPARISON.csv).

CURRENT uses only earlier eligible outcomes in the evaluation season for fitting. Common feature memory can still include older2022-start NFL history; strict-current input/prior policy is separate. RECENT uses the preceding season plus earlier evaluation-season outcomes where supported; MULTI expands from2022without pre2022history. No history arm uses target-game or later-season labels for its original fit.

FULL_SYSTEM includes startup fallbacks, sparse cases and missing labels. LEARNED_ONLY/FALLBACK_ONLY are each procedure’s own disjoint masks, not a shared learned population across competitors. Existing adjacent-history common-mask comparisons remain in checkpointD; these new own-mask numbers must not replace them.

Saved target/player/game IDs produce exact scored masks, unique games and players. Tail P90/P95 are explicitly not computed in this sufficient-stat split; weekly quantiles cannot be pooled. Exact maximum absolute error, strict/inclusive precision, signed bias and fallback counts are retained. Chart lower medians use the exact0.02grid for tolerances; that scoring rule is not a prediction improvement.

Every full-system recipe/week n×MAE/MSE/bias sum matches the existing valid weekly scoreboard; source-bound2025specialization repair replaces its losing original version only in the current view. All original and corrected rows remain preserved. Missing historical prop lines or original leans do not block this numerical benchmark. No offered-threshold, original-selection, EV or ROI result is invented.

[All new startup-window numerical views](STARTUP_NUMERICAL_RESULTS.csv) · [Canonical scores](SCORES.json) · [Execution/coverage checks](RUN_RECEIPT.json) · [Frozen procedure/source roster](../FROZEN_PROTOCOL.json).
