# Local source overrides

Each directory corresponds to an independent clone listed in `../repositories.json`.
Its `tracked.patch` is a Git binary-capable diff against that checkout's recorded
HEAD. `files/` contains the captured untracked source files, including local docs
and scripts. Source files retain their executable modes. Build outputs, firmware,
caches and non-source files stay in their original local project directories;
any non-ignored omissions are listed in the manifest.

To reconstruct a project elsewhere, clone its URL, check out the exact recorded
HEAD, and start with a clean working tree. Apply its patch and then copy its
untracked sources to the same relative paths. For example, from `~/ypcb`:

```bash
git -C openFPGALoader apply --check "$PWD/local-overrides/openFPGALoader/tracked.patch"
git -C openFPGALoader apply "$PWD/local-overrides/openFPGALoader/tracked.patch"
```

These patches describe changes already present in the current local clones;
do not apply them a second time here. During preparation, each tracked patch
passed `git apply --reverse --check` against its matching local working tree.
Every exported source copy has a byte count and SHA256 in `repositories.json`.
OpenTPU source is committed in its own repository, not duplicated here.
