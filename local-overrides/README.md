# Local source overrides

These overlays reconstruct independent projects from the exact base revisions
in [`../repositories.json`](../repositories.json). `tracked.patch` changes files
already present at that base; `files/` supplies additional source, scripts,
documentation and tests. Build outputs, proprietary firmware, caches and recovery
archives are excluded. The base capture was made on October 15; the overlays
were reviewed and updated on October 23. They are no longer byte-for-byte
snapshots of all current live clones.

The manifest's `snapshot_utc`, `path` and `head` preserve the original capture
and patch base. `overrides_updated_utc`, sizes and hashes describe the currently
versioned overlays. The [current project inventory](../docs/PROJECTS.md) has
live checkout locations and a separate dated Git snapshot. In particular,
Bonetto now lives at `~/bonetto-soc`, not the old `projects/bonetto-soc` path.
Do not change a patch's recorded base merely to match a newer live HEAD.

## Reconstruct in a clean checkout

Clone the manifest's URL into a new destination, check out its recorded `head`,
then check and apply `tracked.patch` if that entry has one. Copy `files/.` into
the checkout root, preserving modes. For example, with this tooling checkout
and a **new, clean** Bonetto checkout selected explicitly:

```bash
export YPCB_ROOT="$HOME/ypcb"
export BONETTO_REVIEW_ROOT="$HOME/bonetto-review"
# First clone the recorded URL to BONETTO_REVIEW_ROOT and check out
# f6eea6c8ed9d79322a6ee8e9fd5a1ffccf57cb96 there.
overlay="$YPCB_ROOT/local-overrides/projects-bonetto-soc"
git -C "$BONETTO_REVIEW_ROOT" apply --check "$overlay/tracked.patch"
git -C "$BONETTO_REVIEW_ROOT" apply "$overlay/tracked.patch"
cp -a "$overlay/files/." "$BONETTO_REVIEW_ROOT/"
```

`BONETTO_REVIEW_ROOT` above selects the checkout destination. The separate
`BONETTO_WORKSPACE_ROOT` runtime override selects the parent directory containing
donor projects such as `tiny-gpu`, `etsoc` and `ypcb`; it defaults to `$HOME`.

For `openFPGALoader`, use its manifest base and patch; it has no `files/` tree.
For TiferKing, copy `files/` onto its pinned base; it has no `tracked.patch`.
For the cable reference, apply its descriptor patch and copy its stage2 helper.
Do not reapply patches or overwrite source in the current working clones.
Some of those clones already contain changes, and others have advanced beyond
these overlays. Existing ignored build evidence does not qualify a reconstructed
or edited source tree.

The shared `dlc10-init.sh` uses the stage2 helper directly from this repository's
tracked overlay, so its corrected validation is available without modifying the
independent `ref/inspur-adventures` checkout. Both root `dlc10-*.patch` files
are equivalent compatibility packaging for the current wrapper and helper;
apply **one** only, at a clean destination where those files do not yet exist.
They do not replace the separate `openFPGALoader` source patch or supply firmware.

## Offline verification

First verify every exported byte count and SHA256, including tracked patches:

```bash
python3 - <<'PY'
import hashlib, json, os
from pathlib import Path
root = Path(os.environ['YPCB_ROOT']).resolve()
manifest = json.loads((root / 'repositories.json').read_text())
for repo in manifest['repositories']:
    if repo.get('tracked_patch'):
        data = (root / repo['tracked_patch']).read_bytes()
        if hashlib.sha256(data).hexdigest() != repo['tracked_patch_sha256']:
            raise SystemExit('patch hash mismatch: ' + repo['tracked_patch'])
    for source in repo.get('untracked_sources', []):
        data = (root / source['copy']).read_bytes()
        if len(data) != source['bytes'] or hashlib.sha256(data).hexdigest() != source['sha256']:
            raise SystemExit('source integrity mismatch: ' + source['copy'])
print('All overlay sizes and hashes match')
PY
```

Run the Bonetto regression suite from its reconstructed project root. Its tests
need the base RTL and Makefile in addition to the exported source:

```bash
cd "$BONETTO_REVIEW_ROOT"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The source-level MicroBlaze host tests can run directly from this repository:

```bash
cd "$YPCB_ROOT"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s local-overrides/projects-ypcb_00338_1p1_hack/files/scripts \
  -p test_fedora_soc.py -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tests -p test_dlc10_tools.py -v
```

These checks use mock USB/FTDI/vendor commands, temporary files and, for Bonetto,
Icarus RTL simulation. Python, native C/C++ compilers, libusb/libftdi development
headers and Icarus are needed for all checks; inspect skipped tests if a tool is
missing. Passing them does not establish cable operation, a routed image or
physical DDR behavior. See the [review record](../docs/REVIEW.md) for results.
