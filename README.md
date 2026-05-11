<img width="1920" height="1080" alt="hiddennote" src="https://github.com/user-attachments/assets/55c51112-65f6-425e-b6ef-4ec2bc95c5b2" />


# hiddenote

An encrypted note-taking app built with Python and PyQt6.
All notes are encrypted locally — nothing is sent to any server.

## Features

### Security

- **Argon2id password hashing** with automatic migration from v1 SHA-256 databases
- **AES-256 encryption** (Fernet) with a PBKDF2-derived key
- **Change master password** — re-encrypts all notes transparently
- **Auto-lock** after configurable idle timeout
- **Failed-attempt limit** — 5 wrong passwords closes the app
- **HMAC integrity check** — detects external database tampering on startup
- **Encrypted backup** — copy the database file at any time

### Editor

- **Markdown** editor with live preview (tables, fenced code, TOC, syntax highlighting)
- **Find & Replace** (`Ctrl+H`) with prev / next / replace all and case-sensitive mode
- **Line numbers** (toggle via right-click)
- **Live word & character counter** and line / column indicator in the status bar
- **Insert date & time** at cursor (`Ctrl+Shift+D`)
- **Read-only mode** per note
- **Print** the rendered preview (`Ctrl+P`)
- **Auto-save** with 1.5 s debounce

### Organisation

- **Tags** — multiple tags per note, filter the list by tag
- **Pin** important notes to the top (★)
- **Archive** old notes without deleting them
- **Trash** — soft delete with 30-day auto-cleanup; permanent deletion requires a second confirmation
- **View filters** — All / Pinned / Archived / Trash
- **Sort** by last updated, creation date, or title
- **Rename** notes from the context menu

### Export & Import

- Export notes as **Markdown**, **HTML**, or **plain text**
- Import `.txt` / `.md` files from disk
- Manual database backup from the Settings dialog

### History

- **Version history** — up to 20 snapshots per note, saved on `Ctrl+S` or when leaving the note
- **Restore** any previous snapshot with one click

## Shortcuts

| Shortcut            | Action                                              |
| ------------------- | --------------------------------------------------- |
| `Ctrl+N` / `Insert` | New note                                            |
| `Ctrl+S`            | Save & create version snapshot                      |
| `Ctrl+F`            | Focus note search                                   |
| `Ctrl+H`            | Find & Replace in editor                            |
| `Ctrl+Shift+D`      | Insert current date & time                          |
| `Ctrl+L`            | Lock app                                            |
| `Ctrl+P`            | Print                                               |
| `Delete`            | Move selected note to trash                         |
| Right-click note    | Rename, pin, archive, tags, export, version history |
| Right-click editor  | Toggle line numbers, layout options                 |

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

```text
argon2-cffi
cryptography
Markdown
Pygments
PyQt6
```

### Linux additional dependencies

```bash
sudo apt install -y libxcb-cursor0 libxcb-cursor-dev binutils python3-dev
```

## Installation

```bash
git clone https://github.com/alexchwoj/hiddenote.git
cd hiddenote
pip install -r requirements.txt
python main.py
```

## Building

```bash
# Windows
python build.py --platform windows

# Linux
python build.py --platform linux

# macOS
python build.py --platform macos
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.


## Screenshots
<img width="1200" height="800" alt="image" src="https://github.com/user-attachments/assets/f08b82b4-a9f9-4877-aa9c-dde1ff5eaeb9" />
<img width="1204" height="806" alt="image" src="https://github.com/user-attachments/assets/271a9340-4d2f-45fb-856e-0252506f74b7" />
<img width="1205" height="806" alt="image" src="https://github.com/user-attachments/assets/5d7129b7-0d5e-47d2-a24d-a6a0fce07876" />


## License

MIT — see [LICENSE](LICENSE) for details.
