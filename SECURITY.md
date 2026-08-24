# Security Policy

## Secrets

This repository must never contain a Dida ClientID/LicenseKey pair, an Audit access key, a Basic Authorization value, an environment file, or a DPAPI-protected credential store.

Do not paste real secrets into GitHub issues, pull requests, discussions, screenshots, logs, or agent prompts. When reporting a bug, replace every identifier and credential with synthetic values.

## If a secret is exposed

Treat any secret pasted into chat, source control, terminal history, an issue, or a screenshot as exposed. Revoke or rotate it at its issuing system; deleting the visible text is not sufficient because copies may remain in history or logs.

For an exposed teammate Audit key, identify it with `access-key list`, revoke it with `access-key revoke <key-id>`, and issue a new per-user key. For an exposed Dida credential, rotate the credential with Dida and reconfigure only the trusted gateway machine.

## Deployment

The built-in gateway is a small authenticated application server for local development. It binds to loopback by default and does not terminate TLS. Do not expose it directly to the public internet. Remote team use requires a trusted HTTPS tunnel or reverse proxy, network access controls, monitoring, and a separate revocable Audit key for each user.
