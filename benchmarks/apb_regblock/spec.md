# Tiny APB-lite Register Block Spec

The block exposes two 32-bit registers at addresses `0x00` and `0x04`.

Rules:

- Active-low reset clears both registers.
- A write occurs only when `psel && penable && pwrite && pready`.
- Address `0x00` selects `reg0`; address `0x04` selects `reg1`.
- Reads return the selected register during the access phase.
- Invalid addresses assert `pslverr`.
- `pready` is always high for this tiny zero-wait-state model.
