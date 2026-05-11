# fifo_1r1w Benchmark

`fifo_1r1w` is a four-entry single-clock FIFO with one push side and one pop side.

Interface:

- `push_valid`, `push_ready`, and `push_data` form the enqueue handshake.
- `pop_valid`, `pop_ready`, and `pop_data` form the dequeue handshake.
- `full`, `empty`, and `level` expose FIFO occupancy for formal checks.
- `push_fire` and `pop_fire` expose completed handshakes for assertions and coverage.

Required behavior:

- Reset clears occupancy, pointer state, and visible pop data.
- A push without a simultaneous pop increases occupancy by one when the FIFO is not full.
- A pop without a simultaneous push decreases occupancy by one when the FIFO is not empty.
- Simultaneous push and pop preserve occupancy and keep FIFO ordering.
- A full FIFO may accept a push in the same cycle that it pops.
- An empty FIFO does not pop; the design is not fall-through.
- Data returned at `pop_data` is first-in-first-out ordered and remains stable while
  `pop_valid` is high and `pop_ready` is low.

The benchmark intentionally includes labels for RTL bugs, assertion bugs,
assumption/vacuity bugs, testbench stimulus gaps, reachable coverage gaps, and
invalid coverage goals.
