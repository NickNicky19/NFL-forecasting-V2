# The delta archive is freshly restored; the global gate remains blocked

All13 delta parts were read from their positively evidenced private Drive objects and materialized through authenticated raw-file references. Each fresh local part matched its expected bytes/SHA256. The existing verified first tail part was reused; the other12 were freshly downloaded with at most two concurrent readbacks. No source evidence, earlier partial download or failed receipt was deleted or overwritten.

The freshly assembled **263,613,679-byte** delta matches whole-archive SHA256 `3ac59cf6888faae55ded308042c05f00bbdf474d3c10b35974dc801d60a1175f`. Streaming checks verified all **1,788 regular members**:1,787 content-addressed blobs plus the private map. Every blob matched its name, byte count and hash, covering **4,255 frozen path aliases**. No inner filesystem extraction or model decoding was needed.

The compact embedded map (`4a9a130c…`,12,571,859bytes) and deterministic pretty external encoding (`e592881a…`,15,376,953bytes) were checked separately and proved semantically identical. Their bytes were not falsely called identical. The fixed map retains29,527 path aliases /20,217 unique hashes, and20 accepted prior proof objects revalidate. This one newly complete archive does not replace the other three required archives.

**The root's uploader encountered confirmed `storageQuotaExceeded` during the upload wave.** The successful old-part transfers total15 parts /296,829,898bytes. This limited complete fresh restoration to the delta. The remaining backlog is **38 parts /796,917,760bytes**:

| Archive | Positive uploaded parts | Missing parts | Missing upload bytes | Full fresh archive |
|---|---:|---:|---:|---|
| 2022 |1/11 |10 |209,715,200 |No |
| 2023 complete |1/17 |16 |335,544,320 |No |
| 2024 |11/23 |12 |251,658,240 |No |
| Recovery delta |13/13 |0 |0 |Verified |

The complete archive is the **delta**, not2022. Its uploaded receipt identities were checked before completing readback. All already downloaded partial-season parts remain retained; no additional partial-season fetches followed the narrowed scope. A total21 fresh part files /422,659,018bytes are preserved across the delta and earlier in-flight partial readbacks. The source agent performed no uploads or sharing changes.

[The immutable archive proof](DELTA_FRESH_RESTORATION_RECEIPT.json) records whole/member/map validation. Its `new_downloads:0` describes the local verification stage, which makes no transfers; the linked private source manifest records all13 actual fresh part readbacks. [The overall readback summary](../DELTA_READBACK_AND_RESTORATION_SUMMARY.json) separates those stages and counts. Raw metadata/fetch references and normalized receipts remain private, with public-safe hashes. The single-delta adapter and shared stream core were independently reviewed before execution; independent review of actual recovered bytes and provider chains follows separately.

**No global recovery PASS, model-worker release, new NFL fit, forecast, score, production change or wager follows.** The original expanded gate remains unchanged. Finishing the remaining38 uploads and their complete fresh restores is still required, together with the applicable new-study input/resource/admission checks. Folder ownership and connected-profile identity do not establish whose quota is available; the provider failure and precise owner dependency are retained in the [root's quota checkpoint](../../RECOVERY_PROGRESS_CHECKPOINT_K_V2_QUOTA_STOP.json).
