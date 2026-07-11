# WudiTask Hub

This repository is the shared task-data Hub for
[WudiTask](https://github.com/ChaoWao/wuditask). It intentionally contains no
CLI, agent skills, schemas, tests, or dashboard source.

The current tree contains only:

- `hub.json`: the strict task schema and tool API contract;
- `data/open/`: open and claimed tasks;
- `data/archive/`: immutable task outcomes;
- `.github/workflows/pages.yml`: validation and read-only Pages deployment.

Install the separate tool repository and register this remote:

```bash
python3 /path/to/wuditask/tools/wuditask.py --json install \
  --hub-remote https://github.com/ChaoWao/wuditask-hub.git \
  --hub-branch main
```

Task mutations must go through the WudiTask CLI. The Hub branch accepts
ordinary pushes because a confirmed push is the task-claim synchronization
point. Force pushes and default-branch deletion should remain disabled.
