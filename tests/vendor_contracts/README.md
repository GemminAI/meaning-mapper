# vendor_contracts

正本は sensos の `docs/architecture/contracts/nvs/meaning-measurement.schema.json`。
frame の正本は `docs/architecture/contracts/nvs/meaning-frame.schema.json`。
blob の正本は `docs/architecture/contracts/common/blob.schema.json`。
commit とハッシュの形は `LOCK.json` に書いてある。

ここにあるのは SHA-256 lock 付きの固定コピーである。schema は直接編集しない。

更新は 3 つ。正本を直す。コピーを差し替える。`LOCK.json` の SHA-256 を更新する。

バイト一致は `test_vendor_contract_bytes_match_the_lock` と
`test_vendor_contracts_match_sensos_when_the_directory_is_set` が確認する。
