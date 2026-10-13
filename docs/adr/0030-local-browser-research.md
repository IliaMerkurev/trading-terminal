# ADR 0030: Local browser transport for the research workspace

Date: 2026-10-10. Status: implemented; recovered-source focused automated verification passed. Prior real-browser acceptance is historical; fresh graphical acceptance is pending.

## Decision

The owner authorized a working local browser mode after native Linux graphical
startup was blocked by the validation machine's missing system WebKit helpers.
This supersedes ADR 0029's exclusion of a browser adapter only. Windows/Tauri,
NautilusTrader, saved schemas, product version and financial calculations stay
unchanged. Browser mode uses the same AppService command dispatcher and managed
workers, with no alternate engine or frontend calculations.

Use Python's standard-library HTTP server bound only to 127.0.0.1 and serve a
fixed inventory of the built frontend. Commands remain serial and use the
existing versioned JSON envelope and 1 MiB request/response budget. An explicit
absolute data root is required. The existing exclusive workspace lock prevents
a desktop and browser host from opening the same workspace together.

## Browser boundary

Require the exact numeric loopback Host and port; reject foreign/null Origin,
foreign fetch metadata, duplicate security headers and cross-origin preflights.
A same-origin bootstrap fetch with a custom header obtains a random per-launch
session token. Reads and writes to application APIs require that token in a
custom header. POST also requires an exact same-origin Origin, JSON content type
and bounded Content-Length, with no transfer encoding. No wildcard CORS,
authentication cookies, tokens in URLs, persistent credentials, service worker,
remote deployment, new dependency or account integration is introduced.

Session material stays in frontend memory and server memory. Responses are
no-store, MIME-sniffing is disabled, framing is denied and content is restricted
to self-hosted assets. Inline styles remain necessary for the existing chart and
graph UI; inline scripts are prohibited. The server does not log requests.
Static files are limited to the dist inventory; no directory listing, arbitrary
path serving or SPA fallback is provided. Export downloads require an explicit
launch-local grant from a successful archive_export response, a strict generated
basename, unchanged size/hash and the authenticated same-origin transport.

This prevents hostile websites from reading or mutating a local workspace.
It is not isolation against other local processes or malicious software running
as the same OS user, which already has access to the workspace. Imported Python
remains subject to the platform's existing execution restrictions and consent.

## Lifecycle

Closing/reloading a tab does not stop the service or its workers. State is held
by the existing service and durable storage; reload reconnects and retrieves
active work. The UI explains this and offers explicit confirmed shutdown.
No unload handler mutates state, no failed write is automatically retried, and
no startup automatically resumes an interrupted calculation. Stop local service,
SIGINT and SIGTERM close the existing service/managers and release workspace
ownership. Existing platform supervisors govern unexpected process death.

## Alternatives and limitations

A Vite-only preview cannot operate the backend. Relaxing native WebKit sandbox
settings or changing system paths was rejected. A remote/network web service,
multi-user auth, TLS, deployment and packaged browser distributions are outside
this scope. This local server is not a production public web server. A slow local
client can occupy the serial HTTP connection until its bounded socket timeout.
Windows desktop behavior is retained but still requires Windows native
regression evidence before integration. UI redesign is a separate approved
future slice, not implied by this adapter.
