# Exponential Backoff (Concept)

Exponential backoff is a retry strategy where the delay between retries increases exponentially.
It is commonly used in distributed systems to avoid overwhelming a downstream dependency.

A typical backoff pattern:
- attempt 1: wait 1s
- attempt 2: wait 2s
- attempt 3: wait 4s
- attempt 4: wait 8s

Backoff is often combined with **jitter** (randomized delay) to prevent synchronized retry storms.