# Aera for Home – Home Assistant integration

Custom integration for [Aera for Home](https://www.aera.com/) smart fragrance diffusers.

Aera diffusers are built on the Ayla Networks IoT cloud and have no usable local API, so this
integration polls the cloud (every 60 s) using your Aera app account. It is built on the
[`aeraforhome`](https://pypi.org/project/aeraforhome/) library.

## Installation

### HACS (recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed.
2. In Home Assistant open **HACS → ⋮ (top right) → Custom repositories**.
3. Add `https://github.com/graemer-org/aera-home-ha` with type **Integration**, then click **Add**.
4. Search HACS for **Aera for Home**, open it and click **Download**.
5. Restart Home Assistant.

[![Open your Home Assistant instance and open a repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=graemer-org&repository=aera-home-ha&category=integration)

### Manual

Copy `custom_components/aera` into the `custom_components` folder of your Home Assistant
configuration directory and restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration** and pick **Aera for Home**.
2. Sign in with the email and password you use in the Aera app.

Each diffuser on the account becomes a device, named after its room in the Aera app.
If your password changes, Home Assistant will ask you to reauthenticate.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=aera)

## Entities

| Entity | Type | Devices | Notes |
| --- | --- | --- | --- |
| *(device name)* | `fan` | all | On/off; percentage maps to intensity 1–10 (full-size) or 1–5 (Mini) |
| Intensity | `number` | all | 1–10 (full-size) or 1–5 (Mini) |
| Fragrance | `sensor` | all | Name of the loaded fragrance |
| Fragrance remaining | `sensor` | all | % left in the cartridge / vial |
| Fragrance | `select` | Mini | Tell the Mini which vial is loaded (replaces scanning the QR code) |
| Cartridge | `binary_sensor` | full-size | Cartridge inserted / missing |
| Session | `switch` | Aera 3, 3.1, Mini | Start / stop a timed session |
| Session duration | `number` | Aera 3, 3.1, Mini | Length used by the Session switch (15–240 min, stored in HA) |
| Session time left | `sensor` | Aera 3, 3.1, Mini | |
| Connectivity | `binary_sensor` | all | Diagnostic |
| Problem / Error code | `binary_sensor` / `sensor` | all | Diagnostic; raw `error_condition` value |

Controls update optimistically. The diffuser reports its real state on the next poll.

## Troubleshooting

**"This integration does not support configuration via the UI"** means Home Assistant has not
loaded the integration. Make sure you clicked **Download** in HACS (adding the repository alone
does not install it), then restart Home Assistant. If it persists, check **Settings → System →
Logs** for errors mentioning `aera`.

**Settings → Devices & services → Aera for Home → ⋮ → Download diagnostics** dumps the raw Ayla
properties of every diffuser, with email, password, MAC and IP redacted. Please attach the dump
when opening an issue.

To inspect the properties outside Home Assistant:

```bash
pip install aeraforhome==0.4.0
AERA_EMAIL=you@example.com AERA_PASSWORD=... python scripts/probe.py
```

## Development

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt mypy ruff
pytest
ruff check . && ruff format --check .
touch custom_components/__init__.py && mypy -p custom_components.aera; rm custom_components/__init__.py
```

This project is not affiliated with Aera or Ayla Networks.
