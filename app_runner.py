from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app_config import (
    load_json_config,
    parse_runtime_config,
    select_active_accounts,
    validate_runtime_config,
)


@dataclass
class RunResult:
    configured_accounts: int
    active_accounts: int
    selected_account_name: str
    success_count: int
    total_groups: int
    multiple_accounts_detected: bool


RunAccountCallable = Callable[[dict, bool, int, bool], tuple[int, int]]


def run_single_account_from_config(
    config_path: str,
    headless: bool,
    delay: int,
    cli_debug_on_failure: bool,
    run_account_callable: RunAccountCallable,
) -> RunResult:
    raw_config = load_json_config(config_path)
    runtime_config = parse_runtime_config(raw_config)
    validate_runtime_config(runtime_config)

    active_accounts = select_active_accounts(runtime_config)
    if not active_accounts:
        raise ValueError("No hay cuentas activas. Revisa el campo 'suspended'.")

    selected_account = active_accounts[0]
    success_count, total_groups = run_account_callable(
        selected_account.to_legacy_dict(),
        headless,
        delay,
        cli_debug_on_failure,
    )

    return RunResult(
        configured_accounts=len(runtime_config.accounts),
        active_accounts=len(active_accounts),
        selected_account_name=selected_account.name,
        success_count=success_count,
        total_groups=total_groups,
        multiple_accounts_detected=len(active_accounts) > 1,
    )
