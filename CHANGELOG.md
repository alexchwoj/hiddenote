# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-05-10

### Added

#### Security
- **Argon2id password hashing** — replaces plain SHA-256; existing passwords are upgraded automatically on the first successful login
- **Change master password** — re-derives the encryption key and re-encrypts every note and version snapshot with the new password
- **Auto-lock** — configurable idle timeout (5 / 10 / 30 / 60 min); the cipher is cleared in memory and re-authentication is required to resume
- **Failed-attempt limit** — app closes after 5 consecutive wrong passwords
- **HMAC integrity check** — on startup, an HMAC (keyed with the derived encryption key) of all note ciphertext is compared against the stored value; a mismatch triggers a tamper warning
- **Encrypted database backup** — copy the SQLite file to any path via Settings or the import toolbar button

#### Editor
- **Find & Replace** (`Ctrl+H`) — floating dialog with prev / next / replace / replace all and a case-sensitive toggle
- **Live word & character counter** — updates in real time in the status bar below the editor
- **Line / column indicator** — current cursor position shown in the status bar
- **Insert date & time** (`Ctrl+Shift+D`) — inserts `YYYY-MM-DD HH:MM:SS` at the cursor
- **Line number gutter** — optional; toggle from the right-click dock context menu
- **Read-only mode** — per-note; toggle via note context menu; shows `[READ-ONLY]` in the status bar
- **Print** (`Ctrl+P`) — prints the rendered markdown preview via the system print dialog

#### Organisation
- **Tags** — attach multiple tags to any note; filter the sidebar list by tag via the tag combo box
- **Pin notes** — pinned notes always sort to the top and show a ★ indicator
- **Archive** — hide old notes without deleting them; view them in the Archived filter
- **Trash / soft delete** — `Delete` now moves notes to trash; permanent deletion requires a second confirmation from within the Trash view; 30-day auto-cleanup (configurable)
- **View filters** — All / ★ Pinned / Archived / Trash toggle buttons in the sidebar
- **Sort options** — last updated, creation date, title A → Z, title Z → A
- **Rename note** — via the right-click context menu

#### Export & Import
- Export the current note as **Markdown** (.md), **HTML** (.html), or **plain text** (.txt)
- Import a `.txt` or `.md` file from disk; title is auto-deduplicated if it already exists
- Manual database backup from the Settings dialog

#### History
- **Version history** — up to 20 snapshots per note, saved on `Ctrl+S` or when navigating away; deduplicated so unchanged saves don't create extra entries
- **Restore version** — preview any snapshot in the Version History dialog and restore it to the editor with one click

#### UI & UX
- **Statistics dialog** — note counts (total / pinned / archived / trash), tag count, saved versions, oldest note date, last-updated date
- **Settings dialog** — auto-lock timeout, trash auto-cleanup interval, change password, backup now
- **Custom-styled context menu** — dark background, gold hover, rounded corners, styled separators and submenus, matching the app theme
- **Dynamic status-bar corners** — the bottom corners of the status bar round to match the window frame when the editor dock occupies a window corner; recomputed on resize and dock moves
- **Markdown preview** now uses `fenced_code`, `codehilite`, `tables`, and `toc` extensions
- **Sidebar controls** — sort dropdown and tag-filter dropdown above the note list
- **Title-bar quick-action buttons** — stats, settings, import, lock (`Ctrl+L`)
- **Confirm-password field** on first-run password creation
- **Remaining-attempts indicator** in the password dialog after the first wrong attempt

### Changed
- **`Delete` key** now moves notes to trash instead of permanently deleting them — permanent deletion only happens from within the Trash view
- **Password hashing** upgraded from SHA-256 to Argon2id; migrates silently on first login
- **Editor widget** switched from `QTextEdit` to `QPlainTextEdit` — better performance on long documents and required for the line number gutter
- **Markdown preview** requires Pygments for syntax highlighting in fenced code blocks
- **Database schema** extended with new tables (`tags`, `note_tags`, `note_versions`, `settings`) and new columns (`pinned`, `archived`, `in_trash`, `trash_date`) — existing v1.0.0 databases are migrated automatically with no data loss
- **`requirements.txt`** — added `argon2-cffi` and `Pygments`

### Fixed
- Database indices added for `title`, `updated_at`, `pinned`, `archived`, `in_trash`, `note_id` (on versions and tag joins) — addresses slow list loads on large note collections

---

## [1.0.0] - 2025

- Encrypted note storage using PBKDF2-derived key + AES-256 (Fernet)
- SHA-256 password hashing
- Markdown editor with live preview
- Auto-save (1.5 s debounce)
- Full-text search by title
- Frameless custom UI with dark theme and gold accents
- Cross-platform support (Windows, Linux, macOS)
