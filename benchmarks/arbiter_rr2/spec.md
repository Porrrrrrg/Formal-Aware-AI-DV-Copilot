# 2-Client Round-Robin Arbiter Spec

The arbiter accepts two request inputs, `req0` and `req1`, and produces one-hot grant outputs, `gnt0` and `gnt1`.

Rules:

- Reset initializes `turn` to `0`, giving client 0 priority under contention.
- A grant must never be asserted without its matching request.
- At most one grant may be high in a cycle.
- If only one request is asserted, that requester is granted.
- If both requests are asserted, the requester selected by `turn` is granted.
- Under persistent contention, grants alternate by updating `turn` after each contested grant.
