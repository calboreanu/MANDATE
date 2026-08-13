# Complete Originator Archive

The three `part-*` files are a byte-exact split of
`MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip`. No recompression or content
rewrite was performed.

Reconstruct with:

```bash
cat MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip.part-* \
  > /tmp/MANDATE_ORIGINATOR_RETURN_20260812_FINAL.zip
```

The reconstructed file must have SHA-256:

```text
9193189e58b99e8e7655448fbebfc3da5021bca69dc4d43330f051a8040ba0ef
```

Each part is below GitHub's 100 MB hard file limit. The full archive contains
the 3,000 individual shard records, interrupted-attempt evidence, invalid-key
quarantine, repair audits, test logs, paid smoke, code patches, and package
checksum manifest.

