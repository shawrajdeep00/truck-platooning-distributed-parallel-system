# Original CPU-Only Submission

This directory preserves the 20 source/header/test/build files from
`DPS_ESE_Group01.zip` -> `02_Code_and_GPU/DPS-ESE-main.zip` ->
`DPS-ESE-main/DPS/simulation/`.

They are retained unchanged for comparison, apart from Git's line-ending normalization. The archive's compiled `tests/test_leader` binary is intentionally excluded. This directory is historical reference, not a second supported build entry point: the original Makefile and isolated tests have missing fixtures/assumptions that are addressed by the organized top-level build.

Use the top-level `src/`, `include/`, `tests/`, `Makefile`, and `gpu/` for the integrated demonstration. The primary follower adds the GPU intruder-file listener that is absent from this CPU-only follower. The submission also contained that GPU-enabled follower in its separate GPU directory; it matches the working-folder version used for the primary source.

The original upstream MIT notice is preserved in the repository-root `LICENSE`.
