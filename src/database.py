import sqlite3
import hashlib
import hmac
import os
import shutil
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False


class DatabaseManager:
    def __init__(self, db_path="hiddenote.db"):
        self.db_path = db_path
        self.cipher_suite = None
        self._integrity_key = None
        self._last_version_hash = {}
        self.init_db()
        self.run_migrations()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_auth (
                id INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt BLOB NOT NULL,
                hash_algo TEXT DEFAULT 'sha256'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                content BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pinned INTEGER DEFAULT 0,
                archived INTEGER DEFAULT 0,
                in_trash INTEGER DEFAULT 0,
                trash_date TIMESTAMP DEFAULT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_tags (
                note_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (note_id, tag_id),
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER,
                content BLOB NOT NULL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_pinned ON notes(pinned)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_archived ON notes(archived)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_trash ON notes(in_trash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_note ON note_versions(note_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_tags_note ON note_tags(note_id)")

        conn.commit()
        conn.close()

    def run_migrations(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for stmt in [
            "ALTER TABLE user_auth ADD COLUMN hash_algo TEXT DEFAULT 'sha256'",
            "ALTER TABLE notes ADD COLUMN pinned INTEGER DEFAULT 0",
            "ALTER TABLE notes ADD COLUMN archived INTEGER DEFAULT 0",
            "ALTER TABLE notes ADD COLUMN in_trash INTEGER DEFAULT 0",
            "ALTER TABLE notes ADD COLUMN trash_date TIMESTAMP DEFAULT NULL",
        ]:
            try:
                cursor.execute(stmt)
                conn.commit()
            except sqlite3.OperationalError:
                pass

        conn.close()

    def _hash_password(self, password):
        if ARGON2_AVAILABLE:
            ph = PasswordHasher()
            return ph.hash(password), "argon2"
        return hashlib.sha256(password.encode()).hexdigest(), "sha256"

    def _verify_password_hash(self, password, stored_hash, algo):
        if algo == "argon2" and ARGON2_AVAILABLE:
            ph = PasswordHasher()
            try:
                return ph.verify(stored_hash, password)
            except (VerifyMismatchError, VerificationError, InvalidHashError):
                return False
        return hashlib.sha256(password.encode()).hexdigest() == stored_hash

    def _upgrade_to_argon2(self, password):
        new_hash, algo = self._hash_password(password)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_auth SET password_hash = ?, hash_algo = ? WHERE id = 1",
            (new_hash, algo),
        )
        conn.commit()
        conn.close()

    def setup_encryption(self, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT salt, hash_algo FROM user_auth WHERE id = 1")
        result = cursor.fetchone()
        is_first_setup = result is None

        if result:
            salt = result[0]
        else:
            salt = os.urandom(16)
            password_hash, algo = self._hash_password(password)
            cursor.execute(
                "INSERT INTO user_auth (password_hash, salt, hash_algo) VALUES (?, ?, ?)",
                (password_hash, salt, algo),
            )
            conn.commit()

        conn.close()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher_suite = Fernet(key)
        self._integrity_key = key

        if is_first_setup:
            self.create_welcome_note()

    def verify_password(self, password):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, hash_algo FROM user_auth WHERE id = 1")
        result = cursor.fetchone()
        conn.close()

        if not result:
            return False

        stored_hash, algo = result
        if algo is None:
            algo = "sha256"

        verified = self._verify_password_hash(password, stored_hash, algo)

        if verified and algo == "sha256" and ARGON2_AVAILABLE:
            self._upgrade_to_argon2(password)

        return verified

    def change_password(self, old_password, new_password):
        if not self.verify_password(old_password):
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id, content FROM notes")
        notes = cursor.fetchall()
        cursor.execute("SELECT id, content FROM note_versions")
        versions = cursor.fetchall()

        decrypted_notes = []
        for note_id, enc in notes:
            try:
                decrypted_notes.append((note_id, self.decrypt_content(enc)))
            except Exception:
                decrypted_notes.append((note_id, ""))

        decrypted_versions = []
        for v_id, enc in versions:
            try:
                decrypted_versions.append((v_id, self.decrypt_content(enc)))
            except Exception:
                decrypted_versions.append((v_id, ""))

        new_salt = os.urandom(16)
        new_hash, algo = self._hash_password(new_password)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=new_salt,
            iterations=100000,
        )
        new_key = base64.urlsafe_b64encode(kdf.derive(new_password.encode()))
        new_cipher = Fernet(new_key)

        for note_id, content in decrypted_notes:
            cursor.execute(
                "UPDATE notes SET content = ? WHERE id = ?",
                (new_cipher.encrypt(content.encode()), note_id),
            )

        for v_id, content in decrypted_versions:
            cursor.execute(
                "UPDATE note_versions SET content = ? WHERE id = ?",
                (new_cipher.encrypt(content.encode()), v_id),
            )

        cursor.execute(
            "UPDATE user_auth SET password_hash = ?, salt = ?, hash_algo = ? WHERE id = 1",
            (new_hash, new_salt, algo),
        )

        conn.commit()
        conn.close()

        self.cipher_suite = new_cipher
        self._integrity_key = new_key
        self._last_version_hash.clear()
        return True

    def is_first_time(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_auth")
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0

    def lock(self):
        self.cipher_suite = None
        self._integrity_key = None

    def encrypt_content(self, content):
        return self.cipher_suite.encrypt(content.encode())

    def decrypt_content(self, encrypted_content):
        return self.cipher_suite.decrypt(encrypted_content).decode()

    def compute_integrity_hash(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM notes WHERE in_trash = 0 ORDER BY id")
        rows = cursor.fetchall()
        conn.close()

        mac = hmac.new(self._integrity_key, digestmod=hashlib.sha256)
        for note_id, content in rows:
            mac.update(str(note_id).encode())
            if isinstance(content, bytes):
                mac.update(content)
        return mac.hexdigest()

    def verify_integrity(self):
        stored = self.get_setting("integrity_hash")
        current = self.compute_integrity_hash()
        if stored is None:
            self.set_setting("integrity_hash", current)
            return True
        if hmac.compare_digest(stored, current):
            return True
        self.set_setting("integrity_hash", current)
        return False

    def update_integrity_hash(self):
        self.set_setting("integrity_hash", self.compute_integrity_hash())

    def get_setting(self, key, default=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default

    def set_setting(self, key, value):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()
        conn.close()

    def save_note(self, title, content, save_version=False):
        encrypted_content = self.encrypt_content(content)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM notes WHERE title = ?", (title,))
        existing = cursor.fetchone()

        if existing:
            note_id = existing[0]
            cursor.execute(
                "UPDATE notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE title = ?",
                (encrypted_content, title),
            )
            if save_version:
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                if self._last_version_hash.get(note_id) != content_hash:
                    self._last_version_hash[note_id] = content_hash
                    cursor.execute(
                        "INSERT INTO note_versions (note_id, content) VALUES (?, ?)",
                        (note_id, encrypted_content),
                    )
                    cursor.execute(
                        """DELETE FROM note_versions WHERE id NOT IN (
                            SELECT id FROM note_versions WHERE note_id = ?
                            ORDER BY saved_at DESC LIMIT 20
                        ) AND note_id = ?""",
                        (note_id, note_id),
                    )
        else:
            cursor.execute(
                "INSERT INTO notes (title, content) VALUES (?, ?)",
                (title, encrypted_content),
            )

        conn.commit()
        conn.close()

    def load_note(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM notes WHERE title = ?", (title,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return self.decrypt_content(result[0])
        return ""

    def get_all_notes(self, sort_by="updated_at", view="all", tag_filter=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        sort_map = {
            "updated_at": "n.updated_at DESC",
            "created_at": "n.created_at DESC",
            "title_asc": "n.title ASC",
            "title_desc": "n.title DESC",
        }
        order = sort_map.get(sort_by, "n.updated_at DESC")

        view_filters = {
            "trash": "n.in_trash = 1",
            "archived": "n.archived = 1 AND n.in_trash = 0",
            "pinned": "n.pinned = 1 AND n.archived = 0 AND n.in_trash = 0",
            "all": "n.archived = 0 AND n.in_trash = 0",
        }
        where = view_filters.get(view, "n.archived = 0 AND n.in_trash = 0")

        tag_join = ""
        tag_params = []
        if tag_filter:
            tag_join = "JOIN note_tags nt ON n.id = nt.note_id JOIN tags t ON nt.tag_id = t.id"
            where += " AND t.name = ?"
            tag_params.append(tag_filter)

        query = f"""
            SELECT n.title, n.created_at, n.updated_at, n.pinned, n.archived,
                   GROUP_CONCAT(DISTINCT tg.name) as tags
            FROM notes n
            {tag_join}
            LEFT JOIN note_tags ntg ON n.id = ntg.note_id
            LEFT JOIN tags tg ON ntg.tag_id = tg.id
            WHERE {where}
            GROUP BY n.id
            ORDER BY n.pinned DESC, {order}
        """

        cursor.execute(query, tag_params)
        notes = cursor.fetchall()
        conn.close()
        return notes

    def rename_note(self, old_title, new_title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET title = ? WHERE title = ?", (new_title, old_title))
        conn.commit()
        conn.close()

    def delete_note_permanently(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE title = ?", (title,))
        conn.commit()
        conn.close()

    def trash_note(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET in_trash = 1, trash_date = CURRENT_TIMESTAMP, pinned = 0 WHERE title = ?",
            (title,),
        )
        conn.commit()
        conn.close()

    def restore_from_trash(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notes SET in_trash = 0, trash_date = NULL WHERE title = ?", (title,)
        )
        conn.commit()
        conn.close()

    def empty_trash(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE in_trash = 1")
        conn.commit()
        conn.close()

    def auto_clean_trash(self, days=30):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"DELETE FROM notes WHERE in_trash = 1 AND trash_date <= datetime('now', '-{int(days)} days')"
        )
        conn.commit()
        conn.close()

    def toggle_pin(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT pinned FROM notes WHERE title = ?", (title,))
        result = cursor.fetchone()
        new_val = 0
        if result:
            new_val = 0 if result[0] else 1
            cursor.execute("UPDATE notes SET pinned = ? WHERE title = ?", (new_val, title))
        conn.commit()
        conn.close()
        return new_val

    def toggle_archive(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT archived FROM notes WHERE title = ?", (title,))
        result = cursor.fetchone()
        new_val = 0
        if result:
            new_val = 0 if result[0] else 1
            cursor.execute(
                "UPDATE notes SET archived = ?, pinned = 0 WHERE title = ?", (new_val, title)
            )
        conn.commit()
        conn.close()
        return new_val

    def get_all_tags(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM tags ORDER BY name")
        tags = [r[0] for r in cursor.fetchall()]
        conn.close()
        return tags

    def get_note_tags(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT t.name FROM tags t
               JOIN note_tags nt ON t.id = nt.tag_id
               JOIN notes n ON n.id = nt.note_id
               WHERE n.title = ? ORDER BY t.name""",
            (title,),
        )
        tags = [r[0] for r in cursor.fetchall()]
        conn.close()
        return tags

    def set_note_tags(self, title, tag_names):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM notes WHERE title = ?", (title,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            return
        note_id = result[0]
        cursor.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
        for name in tag_names:
            name = name.strip()
            if not name:
                continue
            try:
                cursor.execute("INSERT INTO tags (name) VALUES (?)", (name,))
                tag_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
                tag_id = cursor.fetchone()[0]
            try:
                cursor.execute(
                    "INSERT INTO note_tags (note_id, tag_id) VALUES (?, ?)", (note_id, tag_id)
                )
            except sqlite3.IntegrityError:
                pass
        cursor.execute(
            "DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM note_tags)"
        )
        conn.commit()
        conn.close()

    def get_note_versions(self, title):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT nv.id, nv.saved_at FROM note_versions nv
               JOIN notes n ON n.id = nv.note_id
               WHERE n.title = ? ORDER BY nv.saved_at DESC""",
            (title,),
        )
        versions = cursor.fetchall()
        conn.close()
        return versions

    def load_version_content(self, version_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM note_versions WHERE id = ?", (version_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return self.decrypt_content(result[0])
        return ""

    def export_note_as_text(self, title, path):
        content = self.load_note(title)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def export_note_as_html(self, title, path):
        import markdown as md
        content = self.load_note(title)
        html_body = md.markdown(
            content,
            extensions=["fenced_code", "codehilite", "tables", "toc"],
        )
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; max-width: 860px; margin: 48px auto; padding: 0 24px; color: #23262F; }}
h1,h2,h3,h4 {{ color: #181A20; }}
code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
pre {{ background: #f0f0f0; padding: 16px; border-radius: 8px; overflow-x: auto; }}
blockquote {{ border-left: 4px solid #FFD580; margin: 0; padding-left: 16px; color: #555; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; }}
th {{ background: #f4f4f4; }}
</style>
</head>
<body>
<h1>{title}</h1>
{html_body}
</body>
</html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    def backup_database(self, backup_path=None):
        if backup_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.dirname(os.path.abspath(self.db_path))
            backup_path = os.path.join(backup_dir, f"hiddenote_backup_{ts}.db")
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def get_statistics(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes WHERE in_trash = 0 AND archived = 0")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM notes WHERE pinned = 1 AND in_trash = 0")
        pinned = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM notes WHERE archived = 1 AND in_trash = 0")
        archived = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM notes WHERE in_trash = 1")
        trash = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tags")
        tag_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM note_versions")
        version_count = cursor.fetchone()[0]
        cursor.execute("SELECT MIN(created_at) FROM notes WHERE in_trash = 0")
        oldest = cursor.fetchone()[0]
        cursor.execute("SELECT MAX(updated_at) FROM notes WHERE in_trash = 0")
        last_updated = cursor.fetchone()[0]
        conn.close()
        return {
            "total": total,
            "pinned": pinned,
            "archived": archived,
            "trash": trash,
            "tags": tag_count,
            "versions": version_count,
            "oldest": oldest,
            "last_updated": last_updated,
        }

    def populate_demo_data(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes")
        cursor.execute("DELETE FROM tags")
        cursor.execute("DELETE FROM note_tags")
        cursor.execute("DELETE FROM note_versions")
        cursor.execute("DELETE FROM settings")
        conn.commit()
        conn.close()

        notes = [
            {
                "title": "Project Roadmap Q2 2026",
                "content": """# Project Roadmap — Q2 2026

## Goals

| Area | Target | Status |
|------|--------|--------|
| Backend API | v3 launch | ✅ Done |
| Mobile app | Beta release | 🔄 In progress |
| Analytics dashboard | Design phase | 📋 Planned |
| Documentation | Full rewrite | 📋 Planned |

## Milestones

### May
- [x] Finalize API contracts
- [x] Set up CI/CD pipeline
- [ ] Complete mobile beta build
- [ ] Internal QA pass

### June
- [ ] Public beta launch
- [ ] Onboarding flow redesign
- [ ] Performance benchmarks
- [ ] Write release notes

## Notes

> The mobile team is blocked on the push notification service until the backend API v3 is fully deployed to prod.

Ping @lucas for the dashboard design files when ready.
""",
                "tags": ["work", "planning"],
                "pinned": True,
                "days_ago": 0,
            },
            {
                "title": "Python Cheat Sheet",
                "content": """# Python Cheat Sheet

## List Comprehensions

```python
squares = [x**2 for x in range(10)]
evens   = [x for x in range(20) if x % 2 == 0]
flat    = [item for sub in nested for item in sub]
```

## Dictionary Tricks

```python
# Merge two dicts (Python 3.9+)
merged = dict_a | dict_b

# Invert a dict
inverted = {v: k for k, v in original.items()}

# Default value
count = counts.get("key", 0)
```

## Useful One-liners

```python
# Flatten a list
from itertools import chain
flat = list(chain.from_iterable(nested))

# Most common element
from collections import Counter
most_common = Counter(lst).most_common(1)[0][0]

# Read file lines
lines = open("file.txt").read().splitlines()
```

## f-strings

```python
name = "world"
pi   = 3.14159

print(f"Hello, {name}!")
print(f"Pi is approximately {pi:.2f}")
print(f"{'left':<10} {'right':>10}")
```

## Context Managers

```python
with open("file.txt", "r") as f:
    content = f.read()
```
""",
                "tags": ["dev", "reference"],
                "pinned": True,
                "days_ago": 1,
            },
            {
                "title": "Book Notes — Deep Work",
                "content": """# Book Notes — Deep Work
*Cal Newport*

## Core Idea

The ability to focus without distraction on cognitively demanding tasks is increasingly rare and increasingly valuable. Those who cultivate this skill will thrive.

## Key Concepts

**Deep Work** — Professional activities performed in a state of distraction-free concentration that push cognitive capabilities to their limit.

**Shallow Work** — Non-cognitively demanding, logistical-style tasks, often performed while distracted. Easy to replicate.

## Rules

1. **Work deeply** — Schedule deep work like meetings. Rituals help.
2. **Embrace boredom** — Don't reach for your phone the moment you're bored.
3. **Quit social media** — Apply the craftsman approach: only use a tool if its benefits outweigh its negatives.
4. **Drain the shallows** — Limit shallow work. Schedule every minute of your day.

## Quotes

> "A distracted mind is a lesser mind."

> "Clarity about what matters provides clarity about what does not."

## My Takeaways

- Block 9–12 AM daily for deep work, no exceptions
- Phone in drawer during focus sessions
- End each workday with a shutdown ritual
""",
                "tags": ["books", "productivity"],
                "pinned": False,
                "days_ago": 2,
            },
            {
                "title": "Recipe — Sourdough Bread",
                "content": """# Sourdough Bread

**Yield:** 1 loaf  **Time:** 24 hours (mostly passive)

## Ingredients

| Ingredient | Amount |
|------------|--------|
| Bread flour | 450 g |
| Water (room temp) | 325 g |
| Active starter | 90 g |
| Salt | 10 g |

## Method

### Day 1 — Dough
1. Mix flour and 300 g water. Rest 1 hour (autolyse).
2. Add starter, mix well. Rest 30 min.
3. Add salt + remaining 25 g water. Squeeze through fingers until combined.
4. **Stretch & fold** every 30 min × 4 rounds.
5. Bulk ferment at room temp for 4–6 hours until 50% rise.

### Shaping
6. Dust surface, turn dough out. Pre-shape into a round. Rest 20 min.
7. Final shape: pull edges under to create tension.
8. Place seam-up in floured banneton.

### Day 2 — Bake
9. Cold proof in fridge overnight (8–16 hours).
10. Preheat oven + Dutch oven at 250 °C for 1 hour.
11. Score loaf, bake covered 20 min, uncovered 25 min.
12. Cool on rack for **at least 1 hour** before slicing.

## Tips

- Starter should be bubbly and pass the float test
- Higher hydration = more open crumb, harder to handle
- Steam in the first 20 min is crucial for crust
""",
                "tags": ["recipes", "personal"],
                "pinned": False,
                "days_ago": 3,
            },
            {
                "title": "SQL Quick Reference",
                "content": """# SQL Quick Reference

## Joins

```sql
-- Inner join
SELECT a.name, b.order_date
FROM customers a
INNER JOIN orders b ON a.id = b.customer_id;

-- Left join (keep all from left)
SELECT a.name, b.order_date
FROM customers a
LEFT JOIN orders b ON a.id = b.customer_id;

-- Self join
SELECT e.name, m.name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;
```

## Aggregations

```sql
SELECT
    department,
    COUNT(*) AS headcount,
    AVG(salary) AS avg_salary,
    MAX(salary) AS top_salary
FROM employees
GROUP BY department
HAVING COUNT(*) > 5
ORDER BY avg_salary DESC;
```

## Window Functions

```sql
SELECT
    name,
    salary,
    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank,
    LAG(salary)  OVER (ORDER BY hire_date) AS prev_salary,
    SUM(salary)  OVER (PARTITION BY department) AS dept_total
FROM employees;
```

## CTEs

```sql
WITH top_customers AS (
    SELECT customer_id, SUM(amount) AS total
    FROM orders
    GROUP BY customer_id
    ORDER BY total DESC
    LIMIT 10
)
SELECT c.name, t.total
FROM top_customers t
JOIN customers c ON c.id = t.customer_id;
```
""",
                "tags": ["dev", "reference"],
                "pinned": False,
                "days_ago": 4,
            },
            {
                "title": "Travel — Tokyo Itinerary",
                "content": """# Tokyo Itinerary — October 2026

## Day 1 — Arrival & Shinjuku
- Land at Narita, take Narita Express to Shinjuku
- Check in at hotel
- Evening: Omoide Yokocho (Memory Lane) for yakitori
- Night: Shinjuku Gyoen if open

## Day 2 — Harajuku & Shibuya
- Morning: Meiji Shrine
- Harajuku: Takeshita Street + Ura-Harajuku
- Lunch: Afuri ramen (yuzu shio)
- Shibuya crossing at sunset
- TeamLab Borderless (book in advance!)

## Day 3 — Asakusa & Akihabara
- Morning: Senso-ji temple, Nakamise shopping street
- Lunch: monjayaki in Tsukishima
- Afternoon: Akihabara for electronics / anime
- Evening: Tokyo Skytree observation deck

## Day 4 — Day Trip to Nikko
- 2 h by train
- Tosho-gu Shrine, Yomeimon Gate
- Kegon Falls
- Back by evening

## Budget Estimate

| Category | Amount (JPY) |
|----------|--------------|
| Flights (return) | ¥85,000 |
| Hotel (4 nights) | ¥60,000 |
| Food | ¥30,000 |
| Transport | ¥12,000 |
| Activities | ¥15,000 |
| **Total** | **¥202,000** |

## Useful Apps
- Google Maps (download offline Tokyo)
- Suica (IC card for transit)
- Google Translate (camera mode)
""",
                "tags": ["travel", "personal"],
                "pinned": False,
                "days_ago": 5,
            },
            {
                "title": "Old Draft — Blog Post",
                "content": """# Why I Switched to a Minimal Setup

I used to have three monitors, a mechanical keyboard with custom keycaps, and about 40 browser tabs open at any given time.

Then I spent a week working from a single laptop at a coffee shop in Lisbon.

Something clicked.

The constraint forced focus. Without the option to glance at a second screen, I stopped multitasking. Without my usual tabs, I opened exactly what I needed. My output — actually useful output — went up.

I've since gone back to one monitor. My tab count rarely breaks 10. I close apps I'm not using.

It's not minimalism for aesthetics. It's minimalism as a forcing function.

The best tool for the job is often the one with fewer escape hatches.
""",
                "tags": ["writing"],
                "pinned": False,
                "archived": True,
                "days_ago": 14,
            },
            {
                "title": "Random Ideas",
                "content": """# Random Ideas

- App that shows your top 3 tasks for the day at startup, nothing else
- Chrome extension that replaces the new tab page with a blank + one text field
- A cooking timer that works entirely via keyboard
- Markdown-based personal wiki synced over SSH
""",
                "tags": [],
                "pinned": False,
                "in_trash": True,
                "days_ago": 20,
            },
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for note in notes:
            archived = note.get("archived", False)
            in_trash = note.get("in_trash", False)
            days_ago = note.get("days_ago", 0)
            ts = f"datetime('now', '-{days_ago} days')"
            trash_ts = ts if in_trash else "NULL"

            encrypted = self.encrypt_content(note["content"])
            cursor.execute(
                f"""INSERT INTO notes (title, content, created_at, updated_at, pinned, archived, in_trash, trash_date)
                    VALUES (?, ?, {ts}, {ts}, ?, ?, ?, {trash_ts})""",
                (
                    note["title"],
                    encrypted,
                    1 if note.get("pinned") else 0,
                    1 if archived else 0,
                    1 if in_trash else 0,
                ),
            )
            note_id = cursor.lastrowid

            for tag_name in note.get("tags", []):
                try:
                    cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                    tag_id = cursor.lastrowid
                except sqlite3.IntegrityError:
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_id = cursor.fetchone()[0]
                try:
                    cursor.execute(
                        "INSERT INTO note_tags (note_id, tag_id) VALUES (?, ?)",
                        (note_id, tag_id),
                    )
                except sqlite3.IntegrityError:
                    pass

        conn.commit()

        versions_data = [
            (
                "Project Roadmap Q2 2026",
                [
                    ("5 days ago", "# Project Roadmap — Q2 2026\n\n## Goals\n\nInitial draft, milestones TBD.\n"),
                    ("3 days ago", "# Project Roadmap — Q2 2026\n\n## Goals\n\n| Area | Target |\n|------|--------|\n| Backend API | v3 launch |\n| Mobile app | Beta release |\n\n## May\n- [ ] Finalize API contracts\n- [ ] CI/CD pipeline\n"),
                ],
            ),
            (
                "Python Cheat Sheet",
                [
                    ("4 days ago", "# Python Cheat Sheet\n\n## List Comprehensions\n\n```python\nsquares = [x**2 for x in range(10)]\n```\n"),
                    ("2 days ago", "# Python Cheat Sheet\n\n## List Comprehensions\n\n```python\nsquares = [x**2 for x in range(10)]\nevens   = [x for x in range(20) if x % 2 == 0]\n```\n\n## Dictionary Tricks\n\n```python\nmerged = dict_a | dict_b\n```\n"),
                ],
            ),
        ]

        for note_title, snapshots in versions_data:
            cursor.execute("SELECT id FROM notes WHERE title = ?", (note_title,))
            row = cursor.fetchone()
            if not row:
                continue
            note_id = row[0]
            for (ago_str, snap_content) in snapshots:
                enc = self.encrypt_content(snap_content)
                cursor.execute(
                    f"INSERT INTO note_versions (note_id, content, saved_at) VALUES (?, ?, datetime('now', '-{ago_str}'))",
                    (note_id, enc),
                )

        conn.commit()
        conn.close()

        self.update_integrity_hash()

    def create_welcome_note(self):
        welcome = """# Welcome to hiddenote!

Thanks for trying out hiddenote, an encrypted note-taking app built with Python and PyQt6.

## Shortcuts

- **Ctrl+N** / **Insert** - New note
- **Ctrl+S** - Save & snapshot version
- **Ctrl+F** - Focus note search
- **Ctrl+H** - Find & Replace in editor
- **Ctrl+Shift+D** - Insert date/time
- **Ctrl+L** - Lock app
- **Delete** - Move note to trash
- **Right-click** a note for more options

## Features

- **Encryption** - Argon2 + AES-256 (Fernet)
- **Tags** - Organize notes with multiple tags
- **Pin & Archive** - Keep important notes on top or hidden
- **Trash** - Soft delete with 30-day auto-cleanup
- **Version History** - Up to 20 snapshots per note
- **Export** - Markdown, HTML, plain text
- **Auto-lock** - Configurable idle timeout
- **Integrity Check** - Detects external DB tampering

## Privacy

Everything is encrypted locally. Nothing is sent to any server.

---
*Delete this note anytime with the Delete key.*"""
        self.save_note("Welcome to hiddenote", welcome)
