"""Dump every Ayla property of every Aera diffuser on an account.

Usage:
    pip install aeraforhome==0.4.0
    AERA_EMAIL=you@example.com AERA_PASSWORD=... python scripts/probe.py

Use the output to check the integration's property map against real hardware.
"""

from __future__ import annotations

import asyncio
import json
import os

from aera import AeraApi


async def main() -> None:
    api = AeraApi(os.environ["AERA_EMAIL"], os.environ["AERA_PASSWORD"])
    try:
        await api.login()
        for device in await api.get_devices():
            properties = await api.get_device_properties(device)
            print(f"# {device.dsn} oem_model={device.oem_model} online={device.is_online}")
            print(json.dumps(properties, indent=2, sort_keys=True, default=str))
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
