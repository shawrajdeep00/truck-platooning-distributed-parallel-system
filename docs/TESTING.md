# Tests and Verification

## Running the suites

On Ubuntu/WSL, install `build-essential`, `libcunit1-dev`, and Python 3. From the repository root:

```bash
make -j2 all test-binaries
make test
```

`scripts/run_tests.py` runs every suite even if an earlier one fails, sets a 45-second timeout for each executable, prints a consolidated result, and returns a nonzero status if any suite fails. The standalone CUnit runners now also return nonzero when assertions fail. Check their final CUnit summaries, not inherited unconditional `[PASS]` print statements.

For a single suite, use `make test-heartbeat`, `make test-matrix-clock`, `make test-cruise-control`, `make test-intruder`, `make test-leader-integration`, or `make test-python`.

## Verified snapshot results

The following results were obtained while preparing this organized repository on 2026-10-27 using Ubuntu under WSL, GCC, CUnit 2.1-3, and Python. These are functional checks, not timing or safety certifications.

| Suite | Cases | Assertions | Result |
| --- | --- | --- | --- |
| `heartbeat_test.c` | 6 | 15 | All pass |
| `test_matrix_clock.c` | 11 | 33 | All pass |
| `test_intruder.c` | 11 | 214 | All pass with documented isolated-state fixtures |
| `test_cruise_control.c` | 13 | 28 | 9 cases pass; 4 assertions fail |
| `test_leader_integration.c` | One multi-stage scenario | C `assert` checks | Passes |
| `test_gpu_stream.py` | 7 | Python unittest checks | All pass on Windows and Ubuntu/WSL |

The simulator and every test executable build. Existing warnings include an unused follower clock snapshot, an unused TCP listener parameter, and a signal handler unused in the test-only leader build. These warnings are retained rather than disguising the state of the original production source.

## What each suite checks

### Heartbeat model

The heartbeat suite models a last-message timestamp, a timeout-emitted flag, and a simplified follower state. It tests that formation ignores timeouts, stale control in `CRUISE` or `INTRUDER_FOLLOW` enters `STOPPED`, a timeout is emitted only once until refreshed, and new messages prevent/resume the model's timeout state.

It does **not** link or execute the real `leader_rx_watchdog()` or follower FSM, create sockets, measure scheduling latency, or demonstrate reconnection. Its simplified message handler resumes on any leader message, whereas production resumes motion from `STOPPED` on a cruise-command event. Therefore a passing model test is not proof that every production liveness path behaves identically.

### Matrix clock

Tests cover zero initialization, send/local increments, element-wise maximum merge followed by a local increment, repeated events, zero/large/negative matrix values, and small multi-node helper interactions. Two commented-out invalid-ID/null-pointer cases are not executed. The helpers do not validate arbitrary IDs, and the suite does not verify all actual network paths.

### Intruder helpers

Tests exercise toggling, Boolean detection output, generated speed/duration ranges, helper-based entry/exit state changes, zero-valued input, repeated toggles, and local matrix-clock updates. `tests/support/intruder_fixture.c` supplies the context and shutdown functions normally owned by the follower executable. The tests use the real flag in `src/intruder.c`, not a second duplicate global.

These are helper tests, not a complete follower-FSM integration test. They do not inspect a real TCP notification, confirm a leader acknowledgment, prove false-positive/false-negative rates, validate every malformed sensor value, or prove gap restoration in the production event path. In particular, helper `exit_intruder_follow()` and the inline production `EVT_INTRUDER_CLEAR` handler are not identical code paths.

### Cruise controller and turn queue

Tests cover positive/clamped speed, initialized queue fields, push/pop behavior, turning at a waypoint, empty-queue handling, zero distance, and a few matrix-clock/component expectations. The following assertions remain unchanged and fail against the current implementation:

| Test | Observed reason |
| --- | --- |
| `following_distance_validation` | The given inputs produce `65.25`, not less than `60`. The relative-speed term is positive because the front truck is faster. The test is not a demonstrated emergency response or a clear isolated close-gap slowdown case. |
| `queue_overflow_defect` | The test fills 10 entries, but `TURN_QUEUE_MAX` is 16; the next push is not an overflow. |
| `extremely_high_speed_defect` | The test expects at most `base + 25`, while the current C clamp allows `base + 100`; the example reaches `1100`. |
| `matrix_clock_component` | The test passes an empty turn queue but expects an increment. The implementation returns without a turn or clock increment. |

These are unresolved test/requirement/implementation mismatches, not silently accepted successes. The first case in particular should be reconciled with the intended control requirement; do not treat the list as proof that the controller is safe. No production controller formula or test assertion was changed merely to obtain a pass.

### Leader integration

The integration scenario links the production leader without its `main()`, uses UNIX stream socket pairs to stand in for follower connections, registers followers, verifies assigned IDs/spawn messages/rear topology, adds a fourth simulated connection, disconnects a middle connection, checks reordering, and verifies that an incoming intruder report becomes `EVT_FOLLOWER_MSG`.

This is not an end-to-end TCP/UDP network test and does not run real follower processes. The fourth connection tests leader bookkeeping only; it does not make a four-follower deployment safe with the current four-entry clock. The scenario does not run the leader FSM to verify intruder-response broadcasting or majority voting. No majority-consensus mechanism is implemented.

### Python bridge and publication checks

The Python suite starts a real local bridge subprocess with two synthetic follower logs, checks aggregate GET output and a valid POST-to-file round trip, verifies invalid JSON/unknown POST-path errors, and checks per-follower disconnect marking. Additional checks cover both follower log formats, the leader regex, cleared notebook outputs and Python syntax, and runtime preparation/reset behavior.

It uses only the standard library and needs no CUDA device. It does not run PyTorch, contact Colab/Cloudflare, benchmark the GPU, fuzz all HTTP inputs, or exercise the file event inside a real C follower.

## CI interpretation

The GitHub Actions workflow builds both programs and all C tests, then requires the heartbeat, matrix clock, intruder, leader integration, and Python checks to pass. It also executes the original cruise suite in an explicitly allowed-failure step and writes a warning to the Actions summary if it fails.

A green workflow therefore means the required checks passed, **not** that the four documented legacy cruise failures were fixed. Local `make test` remains strict and returns failure for them.

## Manual checks still needed

- Run one leader and three real followers, verify formation, turns, per-neighbor positions, and membership changes.
- Toggle leader stale mode with `p`; observe follower `STOPPED` and subsequent cruise recovery. Check TCP EOF separately from a stalled connection.
- Exercise emergency propagation under packet loss and connection failure; measure latency before reporting any bound.
- Follow the local GET -> tunnel GET -> notebook POST -> IPC file -> C FSM path and inspect each step.
- Verify the actual CUDA device and compare CPU/GPU timings on an appropriate workload before claiming acceleration.
- Add production-FSM heartbeat tests, malformed-data/ID bounds tests, stable-identity tests, authenticated HTTP tests, and notification failure coverage.
