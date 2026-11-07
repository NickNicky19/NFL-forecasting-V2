# Missing-only recovery preflight after a real provider change

The accepted backlog still has **53 required parts /1,093,747,658 bytes** before the root uploader's new remote-presence check. Every required local part matches its frozen byte count and SHA256. All four canonical local archive hashes and regular-member header counts also match the accepted plan. This preflight performs no upload, download, extraction, reassembly, deletion or model work.

The root's newly uploaded5,362,879-byte K bundle was freshly downloaded and all11 inner members matched. That is a meaningful provider-state change supporting one bounded old-part attempt. It is not proof of1.09GB available quota and does not clear the old recovery gate. The root remains the sole uploader and must exclude exact parts already present in its fresh333-item folder listing before any retry. The source agent does not infer quota identity from a folder owner or connected-profile address.

| Required archive | Missing parts | Missing upload bytes | Full archive bytes | Regular members |
|---|---:|---:|---:|---:|
| V2-PRIVATE-SEASON-2022-V2 |11 |224,693,683 |224,693,683 |1,882 |
| V2-PRIVATE-SEASON-2023-COMPLETE-V1 |17 |353,782,056 |353,782,056 |4,029 |
| V2-PRIVATE-SEASON-2024-V2 |12 |251,658,240 |464,346,512 |5,181 |
| V2-PRIVATE-RECOVERY-DELTA-20261030D-0001 |13 |263,613,679 |263,613,679 |1,788 |

The absolute cheapest required part is delta index012: **11,955,439 bytes**, SHA256 `211c6e524965b7a8cb669b8cd8d5d90dfd8f3b939ac02ecebce0aa7020514da4`. It is actual required recovery content, not another test upload. The smallest complete archive is2022 at224,693,683 bytes; its tail part010 is14,978,483 bytes. Every archive is essential to the existing full gate. Finishing one part or one archive cannot silently release large fits.

The exact private queue includes required remote filename, current local path, part index/hash/bytes, archive ID/hash and local archive path. It contains no new scientific data; all53 entries were verified against the accepted private queue and public plan. Its SHA256 is **`0afa92672d70b356219813941d32937a03e2e1e127dfd272a75e9facb303a289`**. Paths and private storage identifiers stay outside Git. Remote presence is deliberately unknown in this source-agent queue and is resolved by the root's current listing.

The five old entries in `RECOVERY_UPLOADED_PARTS` are **ERROR records**, not successful uploads. The preserved prior response is HTTP403, `storageQuotaExceeded`: “The user's Drive storage quota has been exceeded.” Every error receipt, original local archive, source file and successful older part remains preserved. The new small upload demonstrates changed write behavior; the next old-part result determines whether continuing is supported. No bulk retry is authorized by this preflight.

## Local restore working space

The four complete archives total1,306,435,930 bytes. Restoring2024 must download its already retained parts as well as newly uploaded missing parts, so full fresh download volume exceeds the1,093,747,658-byte missing-upload subtotal.

| Named restoration layout, preserving source evidence | Logical bytes required |
|---|---:|
| Complete fresh downloaded parts for all four archives |1,306,435,930 |
| Fresh complete assembled archives as additional files |1,306,435,930 |
| All inner regular-file payloads, if separately extracted |1,372,397,644 |
| Downloaded parts plus assembled archives; stream-check members without extracting copies |2,612,871,860 |
| Downloaded parts, assembled archives and all extracted inner copies |3,985,269,504 |

These are payload minima for the named layouts, not filesystem-allocation or new-model-output reserves. Add filesystem/directory overhead and working buffers; the preflight names a separate1MiB stream buffer. The conventional fully extracted layout needs about3.712GiB plus that overhead. The observed workspace had approximately13.319GB free and `/tmp` approximately9.441GB free; these are local filesystem readings at the receipt time, not Drive capacity or a continuing reservation. Prefer the workspace restoration area for durable evidence. No existing evidence needs deletion to obtain this working space. Future fitting output capacity must be reserved separately.

The local archive member totals above come from tar headers. **No fresh remote archive or inner-file restoration was performed here.** The original metadata receipt used an overly strong inner-payload field label; [V2](RECOVERY_PREFLIGHT_RECEIPT_V2.json) explicitly corrects that label and preserves [V1](RECOVERY_PREFLIGHT_RECEIPT.json). This is a metadata clarification, not a completed restoration.

## Exact requirements before the existing gate can pass

Use the unchanged [expanded retention validator](../../../nfl_v2/expanded_retention_gate.py), not a newly weakened definition. It requires the exact accepted plan/review/encoding/allowlist digests and all four pending archive IDs. The root must:

1. Upload only still-missing required parts under their exact names and hashes, preserving successful parts and earlier failures.
2. Download **every** required archive part into a fresh restoration area from the approved private store; verify each part and ordering, reassemble the complete archive and match its full byte count/hash.
3. Independently inspect safe archive membership and verify every regular member's recovered bytes against the retained source/manifest hashes, including the1,788-member delta's compact private map. A matching whole-archive hash alone is not an inner-file check or proof that NFL labels are true.
4. Preserve the reviewed equivalence of the external and embedded private-map encodings. Bind all29,527 path aliases /20,217 unique content hashes, the1,787 new delta blobs and the20 accepted prior object proofs at the frozen scope.
5. Publish safe complete-restoration receipts for each archive and the exact aware, nonfuture full-plan gate receipt. Only after the validator passes can independent prefit review, finite output reserve and a separate root worker release be considered.

The separately prepared2,536,759-byte2021 source extension is not included in these53 old-plan parts and has its own retention/admission. Original strict-HGB, older exact D1/D2 and scheduled-window research retain their own input/procedure requirements. Missing offered lines or original picks do not block football-only numerical work. Recovery work does not take the production lease, stop the retained owner's independent capture, or alter any upcoming deadline.

[Machine preflight](RECOVERY_PREFLIGHT_RECEIPT_V2.json) binds the accepted plan, unchanged gate, local byte checks, private-queue hash, new K write/readback proof and actual resource readings. It is explicitly **not a successful full restoration or fitting admission**.
