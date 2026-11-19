# Security

Please report a security problem privately, not in a public issue: use
[**Report a vulnerability**](https://github.com/fbloemhof/ha-home-in-review/security/advisories/new) on the
Security tab. I'll reply as soon as I can.

Fixes go into the latest release only; update to it before reporting.

Home in Review stores tokens you enter (such as a Grafana token for TeslaMate) in Home Assistant's own config
entry storage, and only ever sends them to the address you entered. Reports are served only to signed-in users
(optionally only administrators).
