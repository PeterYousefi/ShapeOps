# Repository governance

The owner explicitly requested public visibility and main-branch protection on 2026-10-19. The repository is public at https://github.com/PeterYousefi/ShapeOps.

`main` requires a pull request, resolved conversations, and an up-to-date branch passing the `application`, `container`, `kubernetes` and `terraform` checks. Force pushing and deletion are prohibited. Administrators are subject to these protections. Independent approvals are not mandatory because this is currently a solo-maintainer workflow; this does not claim independent review.

Verify current remote settings with `python3 scripts/repository_governance.py`. It uses authenticated, read-only `gh api` calls and exits nonzero when settings are missing, weakened, inaccessible or unverifiable. It never updates GitHub settings. The tracked JSON evidence is a point-in-time observation, not a guarantee that settings cannot later change.

Preserve meaningful commit history using normal merge commits after exact-head CI passes; never bypass protection to increase the count. PR #4 merged as `daed6a7` after all four checks passed in run 39317110196, moving remote main to 30 reachable commits. The owner's goal of more than 80 meaningful commits remains outstanding.

The owner separately approved hourly background engineering runs to implement, test, push and merge qualifying work until main exceeds 80 commits. That continuation retains the same CI and protection gates. It does not authorize Azure deployment, paid infrastructure, production promotion or artificial commit padding.
