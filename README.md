# WudiTask Hub

This repository retains legacy execution records for
[WudiTask](https://github.com/ChaoWao/wuditask). Execution migration has not
been performed; this repository is not archived and active records remain intact.

## Business overview has moved

The canonical [WudiTask Pages](https://chaowao.github.io/wuditask/) reads
GitHub business relationships directly. Scope configuration, hourly publishing,
and freshness checks live in the tool repository. This repository no longer
collects or publishes a separate business snapshot.

### Existing execution data is retained

`hub.json`, `data/open`, `data/archive` and `data/deletions` are unchanged.
The business graph does not read them. The sections below describe the
**legacy execution protocol**, pending a separately validated migration to
per-user, canonical-GitHub-task coordination. They are not requirements for
appearing in the business graph. Do not manually delete active records or
run old and new execution writers concurrently during a future migration.

## Source of truth

Every WudiTask has a canonical GitHub Issue or pull request. A pull request may
be the task itself; WudiTask never creates a wrapping Issue merely because only
a PR exists. Narrative, scope, constraints, acceptance criteria, discussion,
delivery state, reviews, checks, and human assignment remain on that canonical
GitHub object. WudiTask does not accept a local text source.

Use a source in this order:

1. Reuse a matching PR in the execution repository.
2. Reuse or create an Issue in the execution repository.
3. If that repository cannot host the description, create a fallback Issue in
   this Hub and record the concrete reason.

The Hub task record is deliberately small. It stores the execution repository,
canonical source pointer, creator login, priority, cross-task dependencies, and
current `active_agents`. An archive adds the outcome, result, evidence, and
participants. It does not duplicate the GitHub title, body, or acceptance
criteria.

A fallback task looks like this:

```json
{
  "schema_version": 3,
  "id": "WDT-20260711T120000Z-A1B2C3",
  "repo": "owner/execution-repository",
  "source": {
    "kind": "github_issue_fallback",
    "repo": "ChaoWao/wuditask-hub",
    "number": 42,
    "fallback_reason": "The execution repository has Issues disabled."
  },
  "created_by": "alice",
  "priority": "P1",
  "created_at": "2026-07-11T12:00:00Z",
  "dependencies": [],
  "active_agents": []
}
```

Use the
[Fallback task form](../../issues/new?template=fallback-task.yml) to write the
complete task contract before adding its Hub entry.

## Owners, assignment, and execution

Owners are derived live from GitHub and may contain multiple people:

- a PR is owned by its author and assignees;
- an Issue is owned by its assignees and the authors of closing-linked PRs;
- an ordinary mention or `Refs` link does not create an owner, and a closed,
  unmerged PR no longer contributes an owner.

GitHub assignment and agent execution are intentionally separate. `assign` and
`unassign` only add or remove canonical-source assignees; they do not write Hub
coordination state or start another user's agent. Assignment is useful for
responsibility and discovery but is not a distributed lock.

`execute` starts an agent by adding a `{login, run_id}` entry through an
ordinary, non-force Hub push. That confirmed push is the atomic execution
boundary. Different logins may execute the same task concurrently, while one
login may have at most one active run on a task. The opaque `run_id` prevents a
stale session from releasing or archiving a newer run under the same login.

Without a task ID, execute first selects a ready, idle task assigned to the
current login, then a ready unowned task. It never automatically adopts a task
owned only by other people. An explicit task ID means the user chose to join:
if needed, execute first adds the current login as a co-assignee without
removing existing owners, confirms that GitHub transaction, and then starts the
separate Hub transaction. A successful assignment is not rolled back if the
Hub start later fails.

`release` removes only the authenticated login's exact matching `run_id`; it
does not unassign GitHub or stop another login. `unassign` rejects a login that
still has an active run. Archiving an active task requires the caller's exact
run and clears all active entries while preserving them as participants.
`done` always uses this active-run path. If no agents are active, only the task
creator may archive an explicitly terminal `failed` or `cancelled` result, and
that command must omit `run_id`; stale run IDs are rejected rather than
ignored.

## Read and lifecycle workflow

`wuditask check [TASK_ID]` is the single comprehensive read command. With an ID
it checks one task; without an ID it refreshes all current tasks. It reports
dependency readiness, owners, active agents, pull requests, reviews, checks,
delivery state, and coordination drift. The former `dep-check` and `reconcile`
commands do not exist and have no compatibility aliases.

GitHub completion alone does not unblock downstream work. A task only satisfies
a dependency after its source reaches a compatible terminal state and
WudiTask archives it as `done` with non-empty verification evidence. `failed`
and `cancelled` preserve a concrete terminal result but do not satisfy
dependents.

The standard lifecycle is:

1. Write the complete canonical Issue or PR.
2. Add its minimal Hub entry and dependencies.
3. Assign people on GitHub when responsibility is known.
4. Run `check`, then `execute`; start work only after the Hub push is confirmed.
5. Continue to use the canonical source for discussion and delivery.
6. `release` an abandoned run, or archive the terminal result with evidence.

Task mutations must use WudiTask. The Hub default branch must reject force
pushes and deletion. Every coordination mutation uses an ordinary push; the
tool never force-pushes this repository.

## Execution-record maintenance

For execution-record maintenance, the existing CLI validation remains usable:

```bash
python3 tool/tools/wuditask.py --hub hub --local --json validate
```

## Linking fallback work

A PR that completely delivers a fallback Issue should use a fully qualified
closing reference:

```text
Closes ChaoWao/wuditask-hub#42
```

For an umbrella Issue delivered by several PRs, use ordinary references on the
intermediate PRs and close the Issue only after every acceptance condition is
met:

```text
Refs ChaoWao/wuditask-hub#42
```

Only closing-linked PR authors become Issue owners.

## Erroneous archived records

Normal `done`, `failed`, and `cancelled` records remain in `data/archive/`.
`wuditask delete` is reserved for explicitly identified mistaken, duplicate, or
test archives. It rejects incomplete batches and reverse dependencies, removes
the records in one ordinary Hub commit, and writes a deterministic receipt.
Receipt-covered task IDs stay reserved permanently. Deletion does not change
GitHub or erase Git history, old clones, or old Pages artifacts.

## Installation

Clone the separate tool repository to a stable path, then register this Hub:

```bash
python3 /path/to/wuditask/tools/wuditask.py --json install \
  --hub-remote https://github.com/ChaoWao/wuditask-hub.git \
  --hub-branch main
```

The installer keeps a rebuildable Hub cache under
`${XDG_CACHE_HOME:-$HOME/.cache}/wuditask`; it does not use a disposable clone
as the task source of truth.
