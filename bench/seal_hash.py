import hashlib, os, sys

def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

def collect(root, rel="", exclude_common=False, lines=None):
    """Recursively list entries under root. Files -> '<rel> <sha256>'. Symlinks -> '<rel> -> <target>'
    (not descended). exclude_common: skip a top-level 'common' entry entirely."""
    if lines is None:
        lines = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        r = name if not rel else rel + "/" + name
        if exclude_common and r == "common":
            continue
        if os.path.islink(p):
            lines.append(f"{r} -> {os.readlink(p)}")
        elif os.path.isdir(p):
            collect(p, r, exclude_common, lines)
        else:
            lines.append(f"{r} {file_sha(p)}")
    return lines

def tree_hash(root, exclude_common=False):
    lines = collect(root, exclude_common=exclude_common)
    blob = "\n".join(lines)
    return hashlib.sha256(blob.encode()).hexdigest()

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "file":
        print(file_sha(sys.argv[2]))
    elif mode == "tree":
        print(tree_hash(sys.argv[2], exclude_common=("--no-common" in sys.argv)))
