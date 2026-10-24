# WudiTask execution storage

This is the existing execution repository for [WudiTask](https://github.com/ChaoWao/wuditask).
Use its **main** branch. No separate execution branch or business task queue is required.

## One entry

Use **`$wuditask`** (Claude Code: `/wuditask`) and say what you need:
upgrade, inspect a GitHub task, start work, take over here, save progress, or finish.

Existing two-repository installations upgrade in place:

```bash
python3 TOOL/tools/wuditask.py --json upgrade
```

If the old CLI does not yet have `upgrade`:

```bash
python3 TOOL/tools/wuditask.py --json selfupdate
python3 TOOL/tools/wuditask.py --json coord upgrade
```

[Unified skill and upgrade workflow](https://github.com/ChaoWao/wuditask/blob/main/.agents/skills/wuditask/SKILL.md).
Run the upgrade on each machine; original clones and branches remain in use.

## What is stored here

- `data/execution/claims/`: current executions and recovery summaries, keyed by stable GitHub user and task IDs.
- `coordination.json` and `hub.json`: the current execution protocol. Old queue clients reject this format.
- `data/execution/migration.json`: the upgrade record.
- `data/legacy/`: preserved original queue records and manifest, for historical reference only.

The four original task records were retained during upgrade. Historical active entries, if any,
are not marked completed and are not automatically resumed. Git history remains available.

GitHub Issue/PR is the only business record for goals, ownership, progress, design and acceptance.
The [business DAG](https://chaowao.github.io/wuditask/) reads GitHub directly and does not wait
for an execution archive to declare a dependency satisfied.

## Coordination boundary

Different people can share this repository; their execution records are independent.
All machines of one account must use the same branch. Default acquisition avoids duplicate
current runs. Explicit takeover replaces the observed old run without stop proof; it does
not kill processes or retract pending writes. Finishing a run does not close an Issue.

Use ordinary Git transactions through the tool for execution changes. Keep credentials,
private conversations and sensitive checkpoint content out of this public repository.
