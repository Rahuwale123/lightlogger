# Security Policy

lightlogger is a local development tool: it binds to `127.0.0.1` only by
default, runs on a background thread inside your own process, and is off
until you call `lightlogger.start()`. It is not designed to be
internet-facing or to hold up under an adversarial network. The notes below
are scoped to that reality — not an enterprise threat model this project
doesn't need.

## Reporting a vulnerability

Please report security issues privately, not as a public GitHub issue:

- Preferred: use GitHub's private vulnerability reporting feature at
  [github.com/Rahuwale123/lightlogger/security/advisories/new](https://github.com/Rahuwale123/lightlogger/security/advisories/new)
- Alternative: email the maintainer directly via the address listed on the
  [GitHub profile](https://github.com/Rahuwale123)

Please include the lightlogger version, a description of the issue, and
steps to reproduce if you have them. This is a small, part-time project, so
response times aren't guaranteed — but reports will be looked at and
credited.

## Scope

**In scope** — things that would genuinely be a vulnerability in lightlogger:

- `host="0.0.0.0"` (the explicit LAN-exposure opt-in) behaving in a way that
  isn't loudly warned about, or exposing more than the dashboard/log data
- Information disclosure through the dashboard, `/api/logs`, or `/api/stream`
  beyond what the host process itself logged
- A crash or resource exhaustion triggerable by data the dashboard renders
  (e.g. a malicious log message breaking out of the UI's rendering)
- Any dependency-supply-chain issue in the publishing pipeline (lightlogger
  ships zero runtime dependencies by design, so this mainly concerns the
  PyPI Trusted Publishing / CI setup itself)

**Out of scope** — known, accepted characteristics of a localhost dev tool,
not vulnerabilities to report:

- Running lightlogger against a public-facing process, or on a network you
  don't trust, without understanding that `127.0.0.1` binding only protects
  you when you keep it bound there
- Anyone with access to `127.0.0.1` on the machine (or to the LAN, after you
  explicitly opted into `host="0.0.0.0"`) being able to view the dashboard —
  that's the documented behavior, not a bypass
- Denial of service from logging an unreasonable volume of data into your
  own process (the ring buffer bounds memory, but a determined flood is
  still your own CPU/network to manage)

## Supported versions

Security fixes are made against the latest released version on PyPI. There
is no long-term-support branch for older releases.
