# Read-only Drive identity and quota diagnosis

The connected profile matches the approved private companion folder's single owner permission. The profile and normalized file-metadata tools expose no account quota, used-byte or available-byte measurement, so capacity remains unknown from this inspection.

A metadata request for `storageQuota` returned HTTP400 `INVALID_ARGUMENT`: that field does not belong to `files.get`. This is different from the earlier provider HTTP403 `storageQuotaExceeded` upload rejection. No upload, retry, permission change or capacity probe was performed. Matching the owner identity does not resolve that rejection or authorize the blocked fitting queue.

Raw profile, owner-permission and error payloads remain private. The [machine diagnostic](DRIVE_READ_ONLY_DIAGNOSTIC.json) publishes only qualification booleans, safe evidence hashes and null quota fields, with no email, account identifier, folder locator or private path.
