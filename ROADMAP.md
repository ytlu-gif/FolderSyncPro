# Roadmap

This roadmap tracks planned improvements for FolderSyncPro. The current focus
is to make synchronization safer, easier to verify, and more trustworthy before
adding larger platform or cloud features.

## v0.2.0 - Safety and Reliability Update

Goal: reduce the risk of accidental overwrites or deletes, improve comparison
accuracy, and make the project easier to test and maintain.

### 1. Dry Run / Sync Preview

Before running a real sync, FolderSyncPro should be able to preview the planned
actions.

Planned behavior:

- Show how many files will be added, updated, deleted, or marked as conflicts.
- List affected relative paths before execution.
- Let users review risky actions, especially deletes.
- Keep the actual sync behavior unchanged until the user confirms.

Suggested milestone:

- `v0.2.0-alpha.1`

### 2. Conflict File Preservation

Two-way sync should avoid silently overwriting user data when both sides changed.

Planned behavior:

- Detect conflict situations more explicitly.
- Preserve both versions when needed.
- Create conflict copies with clear names, for example:

```text
report.docx
report.conflict-20260928-143000.docx
```

Suggested milestone:

- `v0.2.0-alpha.2`

### 3. Fast Scan

Scanning should stay responsive as project folders grow.

Planned behavior:

- Skip high-churn folders such as `.git`, virtual environments, and caches.
- Use a faster shared scanner for preview, scan, and sync operations.
- Avoid repeated file metadata reads during comparison.

Suggested milestone:

- `v0.2.0-alpha.3`

### 4. Tests

The sync engine should have repeatable tests before larger refactors continue.

Planned test coverage:

- Backup mode adds and updates files without deleting target-only files.
- Mirror mode removes target-only files through the recycle-bin flow.
- Two-way mode syncs new files from both sides.
- Two-way delete propagation works as expected.
- Conflict handling preserves data.

Suggested milestone:

- `v0.2.0-beta.1`

### 5. README Improvements

The project README should help new users understand and trust the tool quickly.

Planned documentation:

- Add main window screenshots.
- Explain backup, mirror, and two-way sync with examples.
- Add Windows installation instructions.
- Add safety notes for delete and conflict behavior.
- Add a short FAQ.

Suggested milestone:

- `v0.2.0`

## Later Ideas

These are useful but should come after the safety-focused v0.2.0 work.

- Restore files from the recycle bin in the UI.
- Export sync history to CSV.
- Add scheduled sync.
- Add system tray support.
- Add GitHub Actions for tests and packaging.
- Add version metadata such as `__version__`.
- Add SFTP, WebDAV, NAS, or cloud storage backends.
- Add automatic update checks.
- Add code signing for Windows releases.

## v0.3.0 - Performance and Indexing Update

Goal: reduce repeated full-folder work for users who run FolderSyncPro often.

### 1. SQLite File Index

FolderSyncPro should maintain a local metadata index for project files.

Planned behavior:

- Store relative path, size, and modified time in SQLite.
- Update source and target snapshots after full sync runs.
- Update individual indexed paths after incremental sync runs.
- Keep the index as a performance cache, not the only source of truth.

Suggested milestone:

- `v0.3.0-alpha.1`

### 2. Incremental Watcher Sync

Folder watcher events should sync only affected relative paths when possible.

Planned behavior:

- Convert watchdog events into relative file paths.
- Send changed paths into the sync engine.
- Avoid full-project scans for common single-file changes.
- Fall back to full scan when no changed path can be identified.

Suggested milestone:

- `v0.3.0-alpha.1`

### 3. USN Journal Acceleration

Windows NTFS can later provide changed file records even when the app was not
running.

Planned behavior:

- Detect whether the folder is on a supported NTFS volume.
- Store the last known USN journal position.
- Resolve changed records back into relative paths.
- Fall back to normal scan on unsupported drives or permission failures.

Suggested milestone:

- `v0.3.0-alpha.2`

## Versioning Notes

FolderSyncPro uses semantic-style version tags:

```text
vMAJOR.MINOR.PATCH
```

Examples:

- `v0.1.0`: first public open-source release.
- `v0.1.1`: small bug fix, no major feature change.
- `v0.2.0`: safety and reliability feature update.
- `v1.0.0`: stable release suitable for general recommendation.
