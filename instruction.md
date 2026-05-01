# Failed Groups Auto-Retry Instruction

## Objective

When the normal publication run fails in one or more groups, always do an automatic retry cycle exactly like the current working flow:

1. Read latest failures from task_log.txt
2. Replace failed-groups config with only those failed IDs
3. Execute failed-groups runner
4. Report retry result from the failed-groups log

## Canonical Files

- Normal run log: task_log.txt
- Failed retry runner: run_failed_groups_test.ps1
- Failed retry log: task_log_failed_groups_test.txt

Note:
- "run_failed_groups" means the canonical script run_failed_groups_test.ps1 in this repo.

## Required Behavior In Every Iteration

1. Never append old failed IDs to new ones.
2. Always overwrite failed config with only failed IDs from the latest normal run.
3. If there are no failed groups, do not run retry and report "no retry needed".
4. If failed IDs are detected, run failed retry immediately.
5. Confirm results from task_log_failed_groups_test.txt (not from task_log.txt).

## Standard Command (No manual IDs)

Use this command first:

powershell -ExecutionPolicy Bypass -File .\run_failed_groups_test.ps1

Reason:
- The script already auto-detects latest failed IDs from task_log.txt when GroupIds is not provided.
- The script generates its temporary failed-groups config outside the project folder.
- The script already runs post_to_groups_selenium.py with that temporary failed config.

## Optional Manual Command (Only if auto-detection fails)

powershell -ExecutionPolicy Bypass -File .\run_failed_groups_test.ps1 -GroupIds 'id1','id2'

## Verification Checklist

After each retry execution:

1. Open task_log_failed_groups_test.txt
2. Find latest summary lines:
   - "RESUMEN [Cuenta 1]: X/Y publicaciones exitosas"
   - "[Cuenta 1]: X/Y publicaciones exitosas"
3. Extract failed IDs from retry run if Y-X > 0
4. If still failed groups remain, run another retry only for those remaining IDs

## Reporting Format

Always report:

1. Retry target count
2. Success count
3. Failure count
4. Failed IDs list
5. Next action (retry remaining or done)

## Safety Rules

- Do not edit config.json for retry flow.
- Do not keep stale failed IDs from previous runs.
- Do not use task_log.txt to report retry result; use task_log_failed_groups_test.txt.
- Keep the retry loop focused only on currently failed groups.
