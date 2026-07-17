# WudiTask Hub

This repository is the shared task-data Hub for
[WudiTask](https://github.com/ChaoWao/wuditask). It also provides a fallback
GitHub Issue tracker for work whose execution repository cannot host the
canonical Issue. It intentionally contains no CLI, agent skills, schemas,
tests, or dashboard source.

The current tree contains only:

- `hub.json`: the task schema and tool API contract versions;
- `data/open/`: open and claimed tasks;
- `data/archive/`: retained outcomes for ordinary tasks;
- `data/deletions/`: durable receipts for explicitly deleted erroneous archives;
- `.github/ISSUE_TEMPLATE/`: the fallback task Issue form;
- `.github/workflows/pages.yml`: validation and read-only Pages deployment.

## Canonical task source

A WudiTask keeps the repository where work executes separate from the source
that describes the work:

- `repo` is the execution repository in `owner/name` form;
- `source` is the canonical GitHub Issue, GitHub pull request, or last-resort
  text description;
- `links` contains auxiliary references and is not the canonical source.

For GitHub-backed work, GitHub owns the description, discussion, assignees,
linked pull requests, reviews, checks, and delivery state. WudiTask owns queue
priority, cross-repository dependencies, the exclusive execution lease in
`claim`, acceptance criteria, verification evidence, and the archived outcome.
Closing a GitHub Issue therefore does not by itself mark a WudiTask done.
Tasks have no separate `owner` field: the GitHub assignee expresses human
responsibility, while `claim` only prevents concurrent execution.

Choose a source in this order:

1. Use an Issue or pull request in the execution repository whenever that
   repository can host the work.
2. Use a WudiTask Hub Issue when the execution repository has Issues disabled,
   the requester cannot create an Issue there, or cross-repository work has no
   suitable single owning repository.
3. Use a text source only when neither the execution repository nor this Hub
   can provide a GitHub Issue or pull request.

When `source.repo` differs from the task's execution `repo`, `fallback_reason`
is required. A Hub-backed task therefore resembles:

```json
{
  "repo": "owner/execution-repository",
  "source": {
    "kind": "github_issue_fallback",
    "repo": "ChaoWao/wuditask-hub",
    "number": 42,
    "fallback_reason": "The execution repository has Issues disabled."
  }
}
```

The last-resort text form records why no GitHub source is available:

```json
{
  "source": {
    "kind": "text",
    "reason": "Neither the execution repository nor the Hub can host an Issue."
  }
}
```

Use the
[Fallback task Issue form](../../issues/new?template=fallback-task.yml) to
capture the execution repository, fallback reason, goal, context, and
acceptance criteria before adding the WudiTask queue entry.

## Linking implementation pull requests

For one pull request that completes a Hub Issue, put the fully qualified
closing reference in the implementation pull request body:

```text
Closes ChaoWao/wuditask-hub#42
```

GitHub closes the Hub Issue when that pull request is merged into its default
branch. WudiTask still requires its own acceptance evidence before the task is
archived as done.

For an umbrella Hub Issue completed by multiple pull requests, do not use a
closing keyword on the individual pull requests. Reference the Issue from each
pull request instead:

```text
Refs ChaoWao/wuditask-hub#42
```

Close the umbrella Issue only after all required pull requests have landed and
the Issue's acceptance criteria have been verified. This prevents the first
merged pull request from reporting the overall work as complete.

## Issue and task-data isolation

GitHub stores Issues outside the Git branch. Creating, assigning, commenting
on, or closing a Hub Issue does not modify `hub.json`, `data/open/`,
`data/archive/`, or the `main` branch, and therefore does not contend with
WudiTask task-data pushes. The Hub Issue is the canonical narrative; the task
JSON remains the scheduling and verification record.

## Pages visibility and token scope

The generated read-only site has three views:

- **Tasks** shows the queue and GitHub delivery state.
- **Dependencies** combines open and archived tasks into a dependency DAG. The
  all-repositories view preserves cross-repository edges and assigns each
  execution repository a distinct color. Selecting one repository shows only
  that repository's tasks and internal edges. Nodes use the canonical Issue or
  pull-request number as their primary label; text-only tasks use the complete
  WudiTask ID.
- **Install** renders the tool repository's canonical `site/install.md` guide;
  the artifact also publishes the Markdown source directly.

The generated Pages snapshot includes canonical source repositories and URLs,
GitHub assignees, closing pull-request authors and URLs, review/check summaries,
delivery timestamps, and query errors, in addition to the task title, goal,
context, claim identity, and acceptance evidence. Treat all of that data as
visible to every Pages reader. Do not publish sensitive task data, and use a
private or access-controlled Pages deployment when repository visibility
requires it.

The default `github.token` is sufficient for public sources. Private
cross-repository sources require a `WUDITASK_GITHUB_TOKEN` secret with the
minimum read access needed for repository metadata, Issues, pull requests,
checks, and commit statuses. The workflow never uses that token to mutate
Issues, pull requests, or task data.

Task mutations must go through the WudiTask CLI. The Hub branch accepts
ordinary pushes because a confirmed push is the task-claim synchronization
point. Force pushes and default-branch deletion should remain disabled.

## Erroneous archived records

Ordinary `done`, `failed`, and `cancelled` outcomes remain in `data/archive/`.
Only when a user explicitly identifies an archived record itself as mistaken,
duplicated, or test data may the dedicated `wuditask delete` workflow remove
it. The CLI requires the configured remote Hub, a concrete reason, exact task
IDs, and a complete batch with no reverse dependency from any task outside the
batch. It never force-pushes.

One Hub commit removes the archived records and writes a durable receipt under
`data/deletions/`. The receipt records the sorted task-ID batch, reason,
verified GitHub identity, and UTC time. Its deterministic ID lets an identical
retry confirm the operation, while a different actor or reason cannot claim
the same deletion. Receipt-covered task IDs are permanently reserved and
cannot be recreated, preventing ABA ambiguity.

Deleting a Hub archive does not close, reopen, assign, or otherwise change its
canonical GitHub Issue or pull request. Git history, existing clones, and
already published Pages artifacts can still contain the original task, so
this workflow is not privacy or secret erasure.

## Installation

Install the separate tool repository and register this remote:

```bash
python3 /path/to/wuditask/tools/wuditask.py --json install \
  --hub-remote https://github.com/ChaoWao/wuditask-hub.git \
  --hub-branch main
```
