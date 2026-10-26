# Episode definitions (prespecified, pending data access)

- Screen-active session: begin only after a verified screen-unlocked/on event; end at the next verified lock/off event; censor at window boundaries.
- Touch within session: retain same-device touch timestamps in the half-open session interval; deduplicate exact timestamp/device/action rows.
- Foreground-app episode: contiguous same-package observations inside a verified screen-active session; do not infer duration from a single isolated package row.
- Keyboard application context: retain same-device keyboard text-state snapshots only when package context is present; compute snapshot intervals after duplicate removal; do not call them keypress intervals.
- Long inactive gap: a gap between consecutive matched events inside a session, reported only after complete event retrieval; threshold must be prespecified before analysis.
