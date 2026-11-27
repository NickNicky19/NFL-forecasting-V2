# Earlier-only category selection across seasons

The registered v2 policy algorithm now has full18-week evaluations in2023,2024and2025, alongside the preserved2026W1–7 replay. All120candidate output recipes share exact query/support/label-value checks in every evaluated week. The generic season-relative choice function reproduces all252previously frozen2026assignments; existing2026scores were not regraded. These are120output recipes across11mechanisms, not120independent learners.

Current score memory selects among historically trained H-MULTI forecasts; it is not a strict-current-football-information model. Training, feature and label vintages remain current/revised source reconstructions under the registered seven-day rule. Each week’s complete scores qualify only after its LAST scheduled game kickoff+7days is strictly before the next fitting origin. All seasons were previously exposed research.

| Season | Current-memory wins / losses / ties versus frozen prior | Current carry MAE | Frozen-prior carry MAE |
|---|---|---:|---:|
| 2023 | 9 / 3 / 0 | 3.111790 | 3.394731 |
| 2024 | 2 / 9 / 1 | 3.005253 | 2.991316 |
| 2025 | 2 / 10 / 0 | 2.883392 | 2.880664 |
| 2026 | 4 / 8 / 0 | 3.049763 | 3.059242 |

The current carry-selector advantage reverses in2025 and2024. In2023 it wins substantially against the frozen2022 choice; the expanding-from2022 startup of that prior score panel is part of this result. No pre2022training is introduced. The2022full frozen-prior policy has no registered2021score panel and remains not applicable under this exact complete-prior-roster rule; source2021statistics alone would not manufacture original2021forecasts.

| Season | Category | n | Frozen prior | Current memory | Delta | Pooled memory | Delta |
|---|---|---:|---:|---:|---:|---:|---:|
| 2023 | anytime_td | 5062 | 0.142731 | 0.142894 | +0.000164 | 0.142731 | +0.000000 |
| 2023 | nick-chart-ppr-v1 | 5713 | 4.492722 | 4.473310 | -0.019412 | 4.477210 | -0.015512 |
| 2023 | pass_att | 663 | 9.102234 | 8.854610 | -0.247624 | 9.655683 | +0.553449 |
| 2023 | pass_cmp | 663 | 6.345951 | 6.025314 | -0.320636 | 6.169089 | -0.176862 |
| 2023 | pass_int | 663 | 0.647059 | 0.657334 | +0.010275 | 0.647059 | +0.000000 |
| 2023 | pass_td | 663 | 0.807616 | 0.802413 | -0.005203 | 0.802678 | -0.004938 |
| 2023 | pass_yd | 663 | 75.599678 | 71.641086 | -3.958592 | 74.587507 | -1.012170 |
| 2023 | rec | 5062 | 1.338601 | 1.294153 | -0.044449 | 1.301659 | -0.036942 |
| 2023 | rec_yd | 5062 | 16.778864 | 16.725007 | -0.053857 | 16.778864 | +0.000000 |
| 2023 | rush_att | 2129 | 3.394731 | 3.111790 | -0.282942 | 3.256883 | -0.137848 |
| 2023 | rush_rec_yd | 5062 | 20.955738 | 20.969870 | +0.014132 | 20.955738 | +0.000000 |
| 2023 | rush_yd | 2129 | 17.973697 | 16.843119 | -1.130578 | 17.433067 | -0.540629 |
| 2024 | anytime_td | 5094 | 0.146578 | 0.147371 | +0.000793 | 0.146578 | +0.000000 |
| 2024 | nick-chart-ppr-v1 | 5742 | 4.512351 | 4.512351 | +0.000000 | 4.512351 | +0.000000 |
| 2024 | pass_att | 664 | 8.430723 | 8.411833 | -0.018889 | 8.430723 | +0.000000 |
| 2024 | pass_cmp | 664 | 5.722892 | 5.727683 | +0.004791 | 5.722892 | +0.000000 |
| 2024 | pass_int | 664 | 0.579819 | 0.605422 | +0.025602 | 0.579819 | +0.000000 |
| 2024 | pass_td | 664 | 0.840361 | 0.827891 | -0.012471 | 0.829819 | -0.010542 |
| 2024 | pass_yd | 664 | 68.692771 | 68.725759 | +0.032988 | 68.692771 | +0.000000 |
| 2024 | rec | 5094 | 1.272085 | 1.274845 | +0.002761 | 1.272085 | +0.000000 |
| 2024 | rec_yd | 5094 | 16.415587 | 16.430686 | +0.015099 | 16.415587 | +0.000000 |
| 2024 | rush_att | 2188 | 2.991316 | 3.005253 | +0.013936 | 2.991773 | +0.000457 |
| 2024 | rush_rec_yd | 5094 | 20.715302 | 20.787072 | +0.071770 | 20.715302 | +0.000000 |
| 2024 | rush_yd | 2188 | 17.646709 | 17.853291 | +0.206581 | 17.646709 | +0.000000 |
| 2025 | anytime_td | 5294 | 0.143650 | 0.143257 | -0.000393 | 0.143483 | -0.000167 |
| 2025 | nick-chart-ppr-v1 | 5937 | 4.365366 | 4.381637 | +0.016271 | 4.365366 | +0.000000 |
| 2025 | pass_att | 664 | 8.488384 | 8.846459 | +0.358075 | 8.488384 | +0.000000 |
| 2025 | pass_cmp | 664 | 5.968566 | 6.064326 | +0.095760 | 5.981972 | +0.013406 |
| 2025 | pass_int | 664 | 0.569277 | 0.573795 | +0.004518 | 0.569277 | +0.000000 |
| 2025 | pass_td | 664 | 0.844880 | 0.844936 | +0.000057 | 0.844880 | +0.000000 |
| 2025 | pass_yd | 664 | 69.016834 | 69.227219 | +0.210384 | 68.929028 | -0.087806 |
| 2025 | rec | 5294 | 1.188704 | 1.181995 | -0.006709 | 1.183037 | -0.005667 |
| 2025 | rec_yd | 5294 | 15.309218 | 15.338041 | +0.028823 | 15.309218 | +0.000000 |
| 2025 | rush_att | 2229 | 2.880664 | 2.883392 | +0.002728 | 2.880664 | +0.000000 |
| 2025 | rush_rec_yd | 5294 | 19.710794 | 19.754135 | +0.043341 | 19.710794 | +0.000000 |
| 2025 | rush_yd | 2229 | 16.780619 | 16.952894 | +0.172275 | 16.738896 | -0.041723 |
| 2026 | anytime_td | 2118 | 0.143144 | 0.145145 | +0.002000 | 0.143144 | +0.000000 |
| 2026 | nick-chart-ppr-v1 | 2359 | 4.502391 | 4.589546 | +0.087156 | 4.502391 | +0.000000 |
| 2026 | pass_att | 242 | 8.406754 | 8.132009 | -0.274745 | 8.481153 | +0.074399 |
| 2026 | pass_cmp | 242 | 5.576454 | 5.433347 | -0.143108 | 5.661762 | +0.085308 |
| 2026 | pass_int | 242 | 0.603306 | 0.629985 | +0.026679 | 0.603306 | +0.000000 |
| 2026 | pass_td | 242 | 0.830579 | 0.863636 | +0.033058 | 0.830579 | +0.000000 |
| 2026 | pass_yd | 242 | 68.732925 | 66.729270 | -2.003655 | 68.332033 | -0.400892 |
| 2026 | rec | 2118 | 1.254958 | 1.259207 | +0.004249 | 1.254958 | +0.000000 |
| 2026 | rec_yd | 2118 | 16.198772 | 16.572238 | +0.373466 | 16.198772 | +0.000000 |
| 2026 | rush_att | 844 | 3.059242 | 3.049763 | -0.009479 | 3.059242 | +0.000000 |
| 2026 | rush_rec_yd | 2118 | 20.125661 | 20.469324 | +0.343662 | 20.125661 | +0.000000 |
| 2026 | rush_yd | 844 | 16.750000 | 17.047393 | +0.297393 | 16.750000 | +0.000000 |

Each older-year directory retains the frozen roster,648choices,4320exact-mask comparisons,36native-score views and paired whole-week bootstrap intervals. Current2026has seven week clusters and retains its insufficient-cluster flag. Full-system fallback contributions stay visible; no new joint common-learned policy claim is inferred from separate per-method fallback rates.

Micro averages below sum n×loss over exactly2023,2024,2025 and divide by their summed n; season-balanced values equally weight those three complete seasons. Current2026W1–7 is never pooled into them. These descriptive aggregates are not new independent NFL observations.
