# Project Materials and Provenance

## Inputs used to prepare this repository

This organized snapshot combines the existing project workspace with the supplied `DPS_ESE_Group01.zip` submission. The supplied ZIP was inspected in memory, including its nested `02_Code_and_GPU/DPS-ESE-main.zip` source archive; archive files were not executed.

| Input | Published location |
| --- | --- |
| Working-folder C source with GPU-enabled follower | `src/` and `include/` |
| Working-folder C tests, including heartbeat | `tests/` |
| Log bridge and Colab notebook | `gpu/` |
| Original CPU-only simulation inside the nested ZIP | `reference/cpu-only/` |
| Original nested-archive MIT license | Root `LICENSE`, unchanged |
| Submitted team PowerPoint | `docs/presentation/truck-platooning-team-1.pptx` |
| Submitted original system-design diagrams | `docs/diagrams/team-design/` |
| Working-folder use-case allocation diagrams | `docs/diagrams/allocation/` |
| Additional allocation exports | `docs/diagrams/reference/` |
| Sequence diagram images and Visual Paradigm source | `docs/diagrams/sequence/` |
| GPU implementation screenshots | `docs/images/` |
| GPU video from the nested source archive/workspace | `docs/media/gpu-implementation-demo.webm` |

The notebook, GPU bridge, and GPU-enabled follower in the supplied ZIP matched the working-folder versions. The CPU-only follower is a different variant and has been retained separately rather than overwritten. Most apparent differences in the other original source files were encoding/line endings or trailing blank lines; the primary header additionally supplies GPU IPC constants.

## Packaging changes

The primary production C source and headers are preserved without behavioral changes. New top-level build paths point to `src/`, `include/`, and `tests/`, placing generated files in `build/` and `bin/`.

The isolated tests receive small state/shutdown fixtures. The intruder suite uses the real production-owned `intruder_flag` instead of defining a duplicate symbol, and declares the existing toggle function in the test. CUnit mains capture assertion failures before cleanup and return a meaningful failing exit code. Existing assertion bodies are preserved, including the four known-failing cruise assertions.

The notebook's cached outputs and execution counts were cleared, its expired tunnel URL was replaced with a placeholder, and its GPU-probe cell was simplified to use `nvidia-smi` when present. The unused CuPy installation was removed; computations still use PyTorch. Its original controller/grid parameters and live-loop behavior are preserved and documented rather than silently rewritten.

Runtime preparation, a bounded test runner, Python bridge tests, a CI workflow, and explanatory documentation were added. Source ZIPs, duplicate GPU code copies, prebuilt executables, object files, historical logs/JSON/CSV/IPC files, unrelated coursework, and a local draft report with student identifiers are not published. The supplied `.url` files are represented by the links below instead of uploading Windows shortcuts or their access-sharing query strings.

## Submitted project links

These references were supplied as shortcuts in the Group 01 archive. They are not additional locally supplied source files and their continued availability has not been verified here.

- [Original team repository](https://github.com/saidurrsaied/DPS-ESE)
- [Original CPU simulation directory](https://github.com/saidurrsaied/DPS-ESE/tree/main/DPS/simulation)
- [Original GPU implementation directory](https://github.com/saidurrsaied/DPS-ESE/tree/main/DPS/GPU%20implementation)
- [Submitted Google Colab notebook](https://colab.research.google.com/drive/1JVvTCj-GT2aPRWp31uPJZzAOVth2FNtJ)
- [Tinkercad follower model](https://www.tinkercad.com/things/exUg6t4zCpb-truck-platoon-gr-1-follower-simplified)
- [Tinkercad overall model](https://www.tinkercad.com/things/c87QRF3iuMf-truck-platoon-gr-1-added-i2c-pbemgintr)

The archive contains links to Tinkercad, not exported Arduino sketches or circuits. Access may require the project owner's sharing settings. No model source or validation is claimed merely because a shortcut exists.

The submitted PowerPoint is retained unchanged with the repository owner's explicit approval to publish its embedded Tinkercad sharing links. The shortcut links listed above omit sharing query strings; this does not remove the links embedded in the original slides.

For a reproducible starting point, open [this repository's cleaned Colab notebook](https://colab.research.google.com/github/shawrajdeep00/truck-platooning-distributed-parallel-system/blob/main/gpu/colab_gpu_cruise_demo.ipynb), then insert the current tunnel URL.

## How to read the materials

Presentations and diagrams preserve the team's submitted design history and may describe intended capabilities more broadly than the code and tests demonstrate. Use the current README, `GPU.md`, `TESTING.md`, and primary source for implementation status. In particular, the current heartbeat monitors TCP-message freshness rather than separate UDP heartbeat packets, intruder handling does not require majority voting, and the test results do not establish a hard real-time or collision-avoidance guarantee.

## Team and license

The project team consists of Bernard Widjaja, Md Saidur Rahman, Meghana Hemesh Kumar, and Rajdeep Shaw. The nested source archive identifies its upstream copyright holder as Md Saidur Rahman and carries an MIT license. That license notice is retained verbatim at the repository root. This repository makes no sole-authorship claim over the collaborative code, slides, or diagrams.
