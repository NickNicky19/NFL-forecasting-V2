# Scoped late PR88 encoding correction

PR88 advanced from `af405c4604f6eac935e594f1acd3ab492eef412c` to **3156058b91c7d9f0bb0f2cdebc4831994214e5bd** during this review. The earlier34-check receipt stays frozen at its stated af405 head. It did not exercise genuine private FIT_START authentication and must not be presented as a pass of the later source or of that missing scope.

The only native-code change is in `authenticate_fit`:

```python
# Before
sha(canonical(recipe) + b'\n')
# After
sha(canonical(recipe))
```

A's owner-local metadata review reports that the genuine original recipe has5722canonical bytes and SHA256 `9c48aab650f35a60631fd5d6af2cef4b8c513416fe0f9b2c61591d7f8af4b85f`, matching the original MODEL_AUDIT and approved parent commitment. Appending one newline makes5723bytes and SHA256 `35b97d56ff4ddfd3460cd6c2d2223499f7390bab885c265550bc13d646a2810a`. The old af405 guard therefore rejected genuine metadata before model inference. This is a recipe-encoding authentication defect, not a measured forecasting loss or grading change.

**B independently verified the exact one-line source delta, changed-function AST census, prepared helper bindings and10 affected checks.** In a separately declared synthetic proof environment, the old guard rejects the newline-free recipe and the new guard returns that same decoded recipe; proof-byte, FIT_START-byte and audit-mismatch checks still reject tampering. No native authority is simulated or claimed. Every other function/class AST, including capture, corrected-mean adapter wiring and public formatting, is unchanged. The original adapter/corrector source hashes and source-profile file remain unchanged.

The new extension is18727bytes, SHA256 `6bf0a6d432d7a0f77bab1d8d8a95c687cf91e350dde48e11a7e827184b469351`. The prepared three-helper Root fragment binds that hash and the unchanged adapter/corrector hashes; its source-profile file commitment also matches the reviewed public bytes. The fragment is **not a full issued Root**. Complete final wire size, authenticated native source/lease/proofs, current query, real inference/durability, readable feed and consumer receipt remain unverified.

B did **not** obtain or load the protected real recipe/FIT_START/proof/capsule. Its actual5722-byte digest and genuine old/new authentication behavior are explicitly attributed to A's owner-local review, whose immutable public report is hash-bound in [B's delta receipt](ENCODER_DELTA_REVIEW_V1.json). Public commitment consistency plus synthetic behavior is not private-row/model parity. No source paths, protected recipe, model or proof bytes are republished.

The owner reports no old af405 native binding or affected NFL output. B measured no historical forecast/grade contamination and invents no transition count. This minimal correction changes authentication of the existing recipe encoding, not model parameters, corrected mean, fallback, selection rule or original qualification record. New helper/source/Root binding and actual operational admission remain required; no five-new-future-week delay is introduced for this correction.

[Executed10-check delta receipt](ENCODER_DELTA_REVIEW_V1.json) · [reproduction code](verify_recipe_encoder_delta_v1.py) · [earlier bounded contract review](README.md).

Command: `python verify_recipe_encoder_delta_v1.py --old-source <authenticated-af405-public-source> --new-source <authenticated-315-public-delta> --out <empty-version-output>`. It extracts only reviewed standard-library metadata functions, uses a visibly synthetic proof fixture, refuses changed source hashes and preserves frozen receipts. Zero NFL fits, inference, model deserializations, issued rows, grades, native API calls or peer writes occurred.

The authorized A owner must review/accept the **latest315head**, satisfy the actual successor source-profile/Root/capsule/FIT_START/proof/current-query requirements under existing guards and execute the registered path. The website owner must retrieve and admit an actual delivered product. This review supplies no merge, workflow dispatch, lease or production authority.
