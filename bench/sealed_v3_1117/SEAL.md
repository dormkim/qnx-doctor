# Seal: sealed hang set v3

Sealed 2026-11-17T08:09:20+09:00 (KST), before any run of qnx-doctor or the baselines on this set. 21 scenarios.

| What | sha256 |
|---|---|
| answers/labels.json (the whole answer key) | `6e86dc691cf0b577096e28c99600c681deb92c0e3273763e2c22a63ff1aff12d` |
| pool/ tree (74 entries: files + the common symlink) | `ddf76515601859d87f30b09867b0d8d172d777645c44ab372df4c0cdbcc22e3d` |
| tests/sealed_hang/common at seal time (shared harness, for information; it may change) | `cbbfa08f9a04ad4781a224b49eda356c40f6114542636e677320f883ce245d04` |

Tree hash = sha256 of the sorted lines «<relative path> <sha256 of file>» (a symlink as «<path> -> <target>»),
joined with newlines, no trailing newline. Verify before the run, from the repo root:

```
sha256sum bench/sealed_v3_1117/answers/labels.json
python3 -c "import hashlib,os;r='bench/sealed_v3_1117/pool';L=[]
for d,ds,fs in os.walk(r):
  ds.sort()
  for f in fs:p=os.path.join(d,f);L.append(os.path.relpath(p,r)+' '+hashlib.sha256(open(p,'rb').read()).hexdigest())
  for x in list(ds):
    p=os.path.join(d,x)
    if os.path.islink(p):L.append(os.path.relpath(p,r)+' -> '+os.readlink(p));ds.remove(x)
L.sort();print(hashlib.sha256(chr(10).join(L).encode()).hexdigest())"
```

The answer key is not edited after this commit; a changed set needs a new seal. Scoring rules: README.md.
