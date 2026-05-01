from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app_config import (
    load_json_config,
    parse_runtime_config,
    select_active_accounts,
    validate_runtime_config,
)
from app_models import AccountConfig


@dataclass
class RunResult:
    configured_accounts: int
    active_accounts: int
    selected_account_name: str
    success_count: int
    total_groups: int
    multiple_accounts_detected: bool


@dataclass
class AccountRunResult:
    account_name: str
    success_count: int
    total_groups: int


@dataclass
class RunSummary:
    configured_accounts: int
    active_accounts: int
    selected_account_names: list[str]
    account_results: list[AccountRunResult]
    multiple_accounts_detected: bool


RunAccountCallable = Callable[[dict, bool, int, bool], tuple[int, int]]


def _select_accounts(
    active_accounts: list[AccountConfig],
    account_name: str | None,
    account_index: int | None,
    run_all_active: bool,
) -> list[AccountConfig]:
    if run_all_active:
        if account_name or account_index is not None:
            raise ValueError(
                "No combines --all-active con --account-name/--account-index."
            )
        return active_accounts

    if account_name and account_index is not None:
        raise ValueError("Usa solo --account-name o --account-index, no ambos.")

    if account_name:
        normalized = account_name.strip().lower()
        for account in active_accounts:
            if account.name.strip().lower() == normalized:
                return [account]

        available = ", ".join(account.name for account in active_accounts)
        raise ValueError(
            f"No existe una cuenta activa con name='{account_name}'. "
            f"Cuentas activas: {available}"
        )

    if account_index is not None:
        if account_index < 1 or account_index > len(active_accounts):
            raise ValueError(
                f"--account-index fuera de rango. Debe estar entre 1 y {len(active_accounts)}."
            )
        return [active_accounts[account_index - 1]]

    return [active_accounts[0]]


def run_accounts_from_config(
    config_path: str,
    headless: bool,
    delay: int,
    cli_debug_on_failure: bool,
    run_account_callable: RunAccountCallable,
    account_name: str | None = None,
    account_index: int | None = None,
    run_all_active: bool = False,
) -> RunSummary:
    raw_config = load_json_config(config_path)
    runtime_config = parse_runtime_config(raw_config)
    validate_runtime_config(runtime_config)

    active_accounts = select_active_accounts(runtime_config)
    if not active_accounts:
        raise ValueError("No hay cuentas activas. Revisa el campo 'suspended'.")

    selected_accounts = _select_accounts(
        active_accounts,
        account_name=account_name,
        account_index=account_index,
        run_all_active=run_all_active,
    )

    account_results: list[AccountRunResult] = []
    for selected_account in selected_accounts:
        success_count, total_groups = run_account_callable(
            selected_account.to_legacy_dict(),
            headless,
            delay,
            cli_debug_on_failure,
        )
        account_results.append(
            AccountRunResult(
                account_name=selected_account.name,
                success_count=success_count,
                total_groups=total_groups,
            )
        )

    return RunSummary(
        configured_accounts=len(runtime_config.accounts),
        active_accounts=len(active_accounts),
        selected_account_names=[account.name for account in selected_accounts],
        account_results=account_results,
        multiple_accounts_detected=len(active_accounts) > 1,
    )


def run_single_account_from_config(
    config_path: str,
    headless: bool,
    delay: int,
    cli_debug_on_failure: bool,
    run_account_callable: RunAccountCallable,
) -> RunResult:
    summary = run_accounts_from_config(
        config_path=config_path,
        headless=headless,
        delay=delay,
        cli_debug_on_failure=cli_debug_on_failure,
        run_account_callable=run_account_callable,
    )
    selected_result = summary.account_results[0]

    return RunResult(
        configured_accounts=summary.configured_accounts,
        active_accounts=summary.active_accounts,
        selected_account_name=selected_result.account_name,
        success_count=selected_result.success_count,
        total_groups=selected_result.total_groups,
        multiple_accounts_detected=summary.multiple_accounts_detected,
    )
