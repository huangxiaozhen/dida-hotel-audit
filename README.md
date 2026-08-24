# Dida Hotel Audit

`dida-hotel-audit` is one reusable Agent Skill for retrieving current Dida Content API static hotel records and letting the active model analyze the fields relevant to the request. It includes deterministic helpers for hotel identity comparison and coordinate-distance checks, plus a generic workflow for all other static-content questions.

The Skill does not create a new Skill for each new question. It fetches the requested hotel records and gives the returned static data to the current model for analysis.

## What installation does—and does not—provide

Installing this GitHub repository installs only the Skill instructions and client code. It does **not** include a Dida ClientID, Dida LicenseKey, Audit access key, or encrypted local credential file, and installation alone does not grant Dida access.

For team use, the components are separated as follows:

```text
Teammate's agent -> installed Skill -> HTTPS Audit gateway -> Dida Content API
                                      ^
                                      individual Audit key
```

- The Dida ClientID and LicenseKey exist only on the trusted gateway machine.
- Each teammate receives an individual revocable Audit key, never the Dida credential.
- The repository and agent prompt contain neither secret.
- The current built-in server listens only on `127.0.0.1` by default. Teammates on other machines need a trusted HTTPS tunnel or deployed gateway URL before they can use the Skill.

## Install from GitHub

The repository must keep `SKILL.md` at its root.

### Codex

Ask Codex:

```text
Use $skill-installer to install the root skill from
https://github.com/huangxiaozhen/dida-hotel-audit
as dida-hotel-audit.
```

If the new Skill does not appear immediately, restart Codex.

### OpenClaw

Install globally:

```powershell
openclaw skills install git:huangxiaozhen/dida-hotel-audit@main --global
```

Omit `--global` for a workspace-only installation.

### Cursor

Open **Customize -> Rules -> Add Rule -> Remote Rule (Github)** and enter:

```text
https://github.com/huangxiaozhen/dida-hotel-audit
```

## Configure a teammate's Audit key on Windows

Do this only after the owner provides a reachable gateway URL and an individual Audit key. Run the command from the installed Skill directory.

The safest setup is hidden input:

```powershell
python -m dida_hotel_audit client configure --gateway-url https://audit.example.com
```

If hidden terminal input cannot paste, copy only the Audit key and use clipboard mode. The program encrypts the key with Windows DPAPI and then clears the clipboard:

```powershell
python -m dida_hotel_audit client configure --gateway-url https://audit.example.com --from-clipboard
```

Check configuration without displaying the key:

```powershell
python -m dida_hotel_audit client status
```

On a non-Windows machine, use the platform's secret manager to inject `DIDA_AUDIT_ACCESS_KEY` and `DIDA_AUDIT_GATEWAY_URL` at runtime. Do not save them in this repository or in an agent prompt.

## Example prompts

```text
用 dida-hotel-audit 的 compare_hotels 判断 Dida 酒店 1062431 和 2333428 是否为同一家酒店。
```

```text
用 dida-hotel-audit 查看 Dida 酒店 3912 的经纬度是否正确，和 Google Maps 的酒店坐标比较，判断差距是否在 1000 米以内。
```

```text
用 dida-hotel-audit 拉取这些酒店的完整静态信息，并根据房型、设施和政策回答我的问题：3912、1062431。
```

## Gateway-owner setup on Windows

Requires Python 3.10 or newer and no third-party packages.

1. Store the Dida credential through hidden terminal input:

   ```powershell
   python -m dida_hotel_audit credentials set --client-id <your-client-id>
   ```

   If hidden input cannot paste, copy only the LicenseKey and use clipboard mode:

   ```powershell
   python -m dida_hotel_audit credentials set --client-id <your-client-id> --from-clipboard
   ```

2. Create a separate access key for each teammate:

   ```powershell
   python -m dida_hotel_audit access-key create --label <teammate-name> --no-save-client
   ```

   Each key is shown once. Transfer it through an approved secret-sharing channel, not chat, email, an issue, or a Git commit.

3. Start the local gateway for development:

   ```powershell
   python -m dida_hotel_audit serve
   ```

   Do not expose the built-in plain-HTTP listener directly to the internet. Put a trusted HTTPS tunnel or reverse proxy in front of it for remote team access.

4. For local owner use, create a key that also saves a DPAPI-protected local client copy:

   ```powershell
   python -m dida_hotel_audit access-key create --label local-owner
   ```

## Direct development checks

With the gateway running, compare two hotels:

```powershell
python scripts/compare_hotels.py 1 2
```

Fetch one to fifty complete static records for model analysis:

```powershell
python scripts/fetch_hotels.py 3912 1062431
```

Fetch one hotel before locating it on a trusted map:

```powershell
python scripts/get_hotel.py 3912
```

After verifying the same property's map marker, calculate the distance:

```powershell
python scripts/audit_coordinate.py 3912 --reference-latitude 0 --reference-longitude 0 --reference-provider "Google Maps" --reference-url "<verified-place-url>"
```

Replace the example reference coordinates and URL with the verified place marker values.

## Security model

- Dida credentials and local Audit client keys are encrypted with Windows DPAPI outside this repository under the current user's local application-data directory.
- Gateway access keys are random 32-character alphanumeric values. The server retains only SHA-256 digests.
- Access keys are never accepted as command-line arguments.
- The gateway does not log credentials or request bodies.
- Revoke one teammate's key without changing the Dida credential:

  ```powershell
  python -m dida_hotel_audit access-key list
  python -m dida_hotel_audit access-key revoke <key-id>
  ```

Never add credentials to this repository, `.env` files, screenshots, prompts, issue reports, or pull requests. See [SECURITY.md](SECURITY.md) before publishing or reporting a security issue.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use synthetic hotel records and mock API responses. They never require or print live credentials.
