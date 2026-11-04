# Resolution: official historical template recovered and copied

The earlier search notes below describe an unsuccessful search stage, not the
current assignment status. The source was subsequently found in module history:
https://github.com/USC-DSO-576-YA/09-audit/blob/03e892ce5bc2f6869675a822f05b630fe8f365c1/change-requests.md

Commit `03e892ce5bc2f6869675a822f05b630fe8f365c1`, root `change-requests.md`.
Its `homework.md` explicitly instructs copying the template into the team root.
Removal commit: `dbcf2ac7b8c62330726d43eb01a54630acec9ec7`.
The exact template was retrieved with `git show` from the local module object
store, preserved in `official-change-requests-template.md`, and copied/populated
as team root `change-requests.md`. Original SHA-256: `03d9ae238a9dd2e11ee7de64250f78bec2c3c5f6a4856e8d3b4098dd565545db`.
No existing teammate shared file was present locally or on live remote main.
The shared-file requirement is now complete.

## Historical search notes (superseded by the resolution above)

# Official shared-template search — October 23, 2026

Result: **not obtained**. Root `change-requests.md` is absent. No teammate entries
are available in the audited tree or working tree; overlap remains unknown.

Sources inspected:

1. Team repository root and audited tree at
   `87a892a392727cfaff176d3c0fbbf6019a60eb4a`.
2. Local `C:/Users/Olga Tovstogan/dso576/09-audit`: README, individual
   `my-audit.md`, AGENTS, tutor, both notebooks, and directory listing including
   hidden directories. Both notebooks' Markdown cells were parsed and read.
   The exercises concern customer totals, tips, delivery rates and a synthetic
   lottery; their concluding "Apply the audit" list gives questions, not a shared
   claims/findings template. Searches also covered notebook code/output text.
3. Local course folders: recursive Markdown/notebook/text searches for
   `change.requests` and `shared.*template`, plus template/change-request filenames.
   Only this audit's own references and `01-onboard/report_template.md` appeared;
   the latter is an onboarding report, not a Module 9 shared claims template.
4. The configured module remote:
   `https://github.com/USC-DSO-576-YA/09-audit.git`.
   The authenticated command below succeeded after sandbox network denial:

```powershell
gh api repos/USC-DSO-576-YA/09-audit/git/trees/HEAD?recursive=1 --jq '.sha, .tree[].path'
```

Live tree commit: `a17432b1b8434f4ac047edd83b71a3d70db7cf9d`, exactly matching
the clean local module HEAD. Thus the inspected local contents match this live
repository version. Its tree contains README, AGENTS, tutor, two notebooks,
`my-audit.md`, `pyproject.toml`, `uv.lock`, `.gitignore`, and the talk-it-through
skill. There is no template directory or shared template file. README points to
`my-audit.md` as the individual template; no shared-template URL was found in
the module README/notebooks. The reference to programming-time slides does not
provide a file or URL for a shared template.

Exact missing source: the instructor/team's official shared **change-requests.md
format**, either the actual file or a course-material location containing it.
It is not supplied by the available Module 9 repository at the commit above.
No access to an unprovided LMS handout is assumed. Obtain that source from the
instructor/team. No replacement was invented and no official template was copied.

Prepared content remains in `audits/olga/proposed-claims-and-findings.md`;
that holding document does not satisfy the actual root shared-file requirement.
