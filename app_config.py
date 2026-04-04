from __future__ import annotations

import json
from typing import Any

from app_models import AccountConfig, RuntimeConfig


def load_json_config(path: str) -> dict[str, Any]:
    # utf-8-sig allows loading files with or without BOM.
    with open(path, "r", encoding="utf-8-sig") as file_handle:
        return json.load(file_handle)


def parse_runtime_config(raw_config: dict[str, Any]) -> RuntimeConfig:
    if "accounts" in raw_config:
        raw_accounts = raw_config.get("accounts", [])
    else:
        raw_accounts = [raw_config]

    if not isinstance(raw_accounts, list):
        raise ValueError("El campo 'accounts' debe ser una lista.")

    accounts = [AccountConfig.from_dict(account) for account in raw_accounts]
    return RuntimeConfig(accounts=accounts)


def validate_runtime_config(runtime_config: RuntimeConfig) -> None:
    if not runtime_config.accounts:
        raise ValueError("No hay cuentas configuradas en el archivo JSON.")

    for account in runtime_config.accounts:
        if not account.groups:
            continue

        for group in account.groups:
            if not group.id:
                raise ValueError(
                    f"La cuenta '{account.name}' tiene un grupo sin 'id'."
                )


def select_active_accounts(runtime_config: RuntimeConfig) -> list[AccountConfig]:
    return [account for account in runtime_config.accounts if not account.suspended]
