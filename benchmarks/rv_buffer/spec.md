# Single-Entry Ready/Valid Buffer Spec

The buffer stores one data beat between an input ready/valid channel and an output ready/valid channel.

Rules:

- Reset clears the buffer.
- `out_valid` is high exactly when the buffer is full.
- `in_ready` is high when the buffer is empty or when the output side is ready to dequeue in the same cycle.
- Data is stable while the output is stalled.
- A simultaneous enqueue/dequeue while full keeps the buffer full and replaces the stored data with the new input beat.
