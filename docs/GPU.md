# GPU Implementation

## Purpose and execution boundary

The GPU extension demonstrates communication between a local distributed C simulation and a remote PyTorch runtime. It has two functions: a display-only cruise-speed calculation and a synthetic intruder generator whose results return to the simulation.

The C processes remain responsible for networking, motion, local cruise control, leader-message freshness, emergency behavior, and state transitions. Python HTTP, JSON parsing, the outer follower loop, and file operations run on CPUs. Only tensors explicitly placed on the selected PyTorch device run on CUDA when a CUDA device is available.

The recorded demonstration used an NVIDIA Tesla T4. The notebook prints the actual selected device; the repository does not require or reserve that particular GPU. A CPU run is useful for functional inspection but is not GPU execution.

## End-to-end data flow

1. The leader and followers write console status to separate log files through `tee`.
2. `gpu/gpu_stream.py` tails those files, parses positions/speeds, and combines each follower's latest observation with the latest observed leader values.
3. The bridge publishes an aggregate `latest.json` and appends individual rows to `stream.csv`.
4. Its HTTP server exposes GET `/latest.json` and accepts POST `/intruder`.
5. An optional Cloudflare tunnel makes that local HTTP service reachable from Colab. Both GET and POST use the same tunnel; no separate tunnel is needed for feedback.
6. Colab fetches the JSON, extracts follower records, computes mirror outputs, and performs the grid-based synthetic intruder scan for each connected sample.
7. Colab posts the sequence number, target follower, active flag, speed, length, and duration to `/intruder`.
8. The bridge writes a complete line to a temporary file and replaces the selected per-follower intruder file.
9. The C follower polls its configured file every `200` ms and converts changes into priority-queue events.
10. The follower FSM handles those events alongside ordinary cruise, distance, watchdog, and emergency events. On initial intruder entry it notifies the leader over TCP.

The path is asynchronous. Console output, polling, HTTP latency, and device synchronization all add delay. It is not a synchronized distributed control tick or a measured real-time guarantee.

## Local log bridge

The bridge uses only Python standard-library modules. It creates one leader-reader thread and one reader thread per configured follower. A reader seeks to the end of its file at startup and waits for new text; old records are not replayed. Carriage returns are treated as record delimiters, which accommodates the C program's terminal-style status updates. A buffered record is processed when its delimiter arrives.

Leader records provide position and speed. Follower records provide state, position, current speed, and gap; the optional printed direction field is accepted by the regular expression. Follower observations are ignored until a leader observation has been parsed. Timestamps are assigned when the bridge parses a record, not when the C physics update originally occurred.

Shared in-memory dictionaries use a lock. A separate file lock serializes publication through the shared `latest.tmp` file before it replaces `latest.json`. This prevents two threads from simultaneously renaming the same temporary file. It does not make independently sampled leader/follower data simultaneous, and CSV appends are not protected by that same publication lock.

Use a single bridge for all configured followers. Use absolute input/output paths because the serving mode changes the process working directory. Put outputs in `runtime/`, not the repository root; the server serves the entire output directory.

### JSON format

This is an illustrative payload, not stored live telemetry:

```json
{
  "ts": 1760000000.0,
  "followers": {
    "1": {
      "ts": 1760000000.0,
      "follower_id": 1,
      "state": "CRUISE",
      "my_x": 0.0,
      "my_y": 10.0,
      "current_speed": 39.0,
      "gap": 10.0,
      "leader_x": 0.0,
      "leader_y": 20.0,
      "leader_speed": 40.0,
      "disconnected": false
    }
  }
}
```

The dictionary key and `follower_id` come from the bridge's manual `id:path` configuration, not an automatic query to the C topology manager. `gap` is the C log's distance to that follower's front reference. The bridge supplies leader coordinates separately; it does not transmit immediate-predecessor coordinates for every follower.

`ts` uses Unix epoch seconds: wall-clock seconds since 1970-01-01 00:00:00 UTC. It is different from the C watchdog's monotonic clock. The C GPU-file reader currently does not reject an old event using this timestamp.

### Disconnection handling

When a follower log contains `[FOLLOWER] Shutdown requested ... tcp recv closed`, the bridge marks that follower as disconnected. A legacy `Leader is disconnected.` message marks the known followers. The notebook prints a disconnected indication, posts a clear event, skips that follower, and stops its loop when all available samples are marked disconnected.

These flags depend on matching logged shutdown text. Quiet logs, a stalled bridge, missing stderr, or a killed process do not automatically become disconnected flags. There is no sample-age timeout in this notebook, and failed POSTs are not made reliable by the flag mechanism.

## PyTorch cruise mirror

`compute_block(sample, device)` builds a floating-point tensor with follower position, leader position, current follower speed, and leader speed. PyTorch computes Euclidean distance, projected error, a relative-speed damping term, a proportional correction, and a clamped speed. The function returns two Python floats: computed gap and new speed. Converting device values with `.item()` synchronizes/copies scalar results to the Python host.

The notebook keeps its original parameters:

| Quantity | Notebook | Local C controller |
| --- | --- | --- |
| Prediction timestep | `0.1 s` | `0.25 s` |
| Normal target gap | `10.0` | `10.0` |
| Proportional / relative-speed gains | `0.35` / `0.70` | `0.35` / `0.70` |
| Extra speed above leader base | `25.0` | `100.0` |
| Front reference | Leader for every sample | Leader for follower 1; immediate predecessor for later followers |
| Intruder-expanded target | Not used by the mirror | `TARGET_GAP + current_intruder.length` |

Consequently the mirror is not an exact replica of the current C controller, especially for followers behind the first truck or during intruder mode. The terminal's displayed `gap` field is the value from the incoming C sample, while `new_speed` is calculated by the notebook. The calculated GPU speed is **not posted back as a motion command**. Only the synthetic intruder fields are posted. TTC was removed and is not computed.

The Python loop visits followers sequentially. PyTorch may parallelize operations within a tensor, but this notebook does not batch all follower samples into a large parallel control workload or demonstrate an acceleration factor.

## Synthetic intruder grid

The grid is a `1000 x 1000` tensor allocated on the selected device. With ordinary `float32` defaults this is one million elements, approximately 4 MB of element storage. It is a demonstration occupancy array, not one million independently tracked vehicles.

| Parameter | Value | Role |
| --- | --- | --- |
| `GRID_SIZE` | `1000` | Grid width and height |
| `GRID_OFFSET` | `500` | Offset from world coordinates to array coordinates |
| `INTRUDER_RADIUS` | `4` | Coordinate offsets and local scan half-width |
| `INTRUDER_PROB` | `0.05` | Approximately 5% spawn probability per processed follower scan |
| `INTRUDER_SPEED` | `40` | Synthetic event speed, not measured from an object |
| `INTRUDER_LENGTH` | `10` | Synthetic event length |
| `INTRUDER_DURATION_MS` | `5000` | Duration field sent with an active event |

For every call to `gpu_intruder_scan(sample)`:

1. Clear the entire grid using `zero_()`; there is no persistent occupancy scene.
2. Read the sample's `my_x` and `my_y`.
3. Map each coordinate through `round(value) + 500`, clamped to `0..999`.
4. Draw a random value. If it exceeds `0.05`, return `False` immediately.
5. Otherwise draw independent integer offsets in `[-4, 4]`, clamp the resulting indices, and mark one grid cell as occupied.
6. Slice the square extending four cells in each direction from the follower's mapped location. Away from boundaries, this slice is `9 x 9`.
7. Sum that slice and return whether the sum is positive.

The synthetic object is deliberately placed inside the area that is scanned, so a spawned object produces a hit. This is random event generation followed by an occupancy check, not perception from a camera, radar, or independent traffic simulation. Only the local slice is summed, not the full million-cell grid. The full grid is cleared on each scan.

Coordinates beyond the representable region saturate at the grid edges. Resetting the grid for each follower means different followers do not observe a common persistent intruder. A reported radius of four is a square/Chebyshev neighborhood in grid indices, not a Euclidean circular detection range.

## Intruder POST and file IPC

An active notebook request has this shape:

```json
{
  "seq": 7,
  "target_id": 2,
  "active": true,
  "speed": 40,
  "length": 10,
  "duration_ms": 5000
}
```

The bridge appends its current wall-clock timestamp and writes:

```text
7 2 1 40 10 5000 1760000000.0
```

`--intruder-out` selects the output pattern. The recommended absolute pattern is `$PWD/runtime/intruder_{id}.txt`. The C process uses the `GPU_INTRUDER_FILE` environment variable to choose its own absolute file path.

The follower remembers its last observed sequence and event values. A different sequence with an activation/deactivation change produces an event; changed parameters while active can also produce an update. Repeated identical active values do not repeatedly enqueue activations. The comparison detects a different sequence; it is not monotonic-sequence or replay protection.

Normal initial activation in `CRUISE` changes the FSM to `INTRUDER_FOLLOW`, stores the intruder, sets the expanded target gap, and reports to the leader. The C cruise controller continues to calculate follower speed using that expanded target. The leader handles a nonzero-speed report by entering `INTRUDER_FOLLOW` and assigning the reported speed to the leader. A zero-speed clear report returns its state to `CRUISE`.

The GPU path carries `duration_ms` but does not start the available intruder timer. Typically a later scan posts `active: false`, ending the episode sooner than five seconds. Clear and active events can be ignored in states that do not handle them, including initial formation; a new file sequence alone does not guarantee a transition in every FSM state.

## Limitations and interpretation

- **No real perception:** Intruders are generated near a follower at random and are guaranteed to be within the scanned neighborhood when spawned.
- **No measured speedup:** Small tensors, Python loops, network requests, and repeated scalar device synchronization can dominate execution. GPU availability is not evidence of a performance benefit.
- **No remote speed actuation:** GPU speed calculations are observational; C remains the motion controller.
- **No hard timing guarantee:** Console decimation, unsynchronized samples, polling, and HTTP delays make this unsuitable as a safety-critical remote control path.
- **No reliable event delivery:** The notebook catches POST exceptions without retrying and does not check POST HTTP status. A later clear may fail to reach the follower.
- **No automatic stale-data rejection:** Quiet telemetry can be processed repeatedly, and event timestamps are not checked for age by C.
- **No stable identity integration:** A topology change can reassign follower IDs while bridge labels/files remain fixed. Restart the three-follower GPU demonstration rather than assuming remapping is automatic.
- **No authentication or production validation:** The public demo endpoint accepts writes, and numeric/range validation is incomplete. Use a trusted temporary session and serve only the runtime directory.
- **No persistent intruder lifetime:** Grid occupancy resets per call, and the duration field is not an enforced hold timer.

Potential future changes include telemetry with stable IDs and real front-neighbor data, consistent CPU/GPU parameters, batched tensor operations, measured CPU/GPU timing with proper synchronization, persistent intruder objects, authenticated/validated requests, explicit event expiry, POST status/retry handling, and an isolated telemetry service instead of parsing terminal logs. These are future work, not implemented claims.

For exact run commands, use the [main README](../README.md#run-the-gpucolab-extension).
