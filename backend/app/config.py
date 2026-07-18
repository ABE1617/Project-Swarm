import os
import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
INSTANCE_DIR = BACKEND_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

# Directory that file nodes (read_file / write_file) are sandboxed to.
FILES_DIR = Path(os.environ.get("SWARM_FILES_DIR", PROJECT_DIR / "data")).resolve()
FILES_DIR.mkdir(parents=True, exist_ok=True)

# Set SWARM_ALLOW_ANY_PATH=1 to let file nodes escape the sandbox directory.
ALLOW_ANY_PATH = os.environ.get("SWARM_ALLOW_ANY_PATH") == "1"

# Drop-in directory for user node files: any .py here becomes a palette node.
NODES_DIR = Path(os.environ.get("SWARM_NODES_DIR", PROJECT_DIR / "nodes")).resolve()
NODES_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("SWARM_DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'swarm.db'}")

# Where the app is reachable for OAuth redirects (register this /api/oauth/google/callback
# as an authorized redirect URI in the Google Cloud Console).
PUBLIC_URL = os.environ.get("SWARM_PUBLIC_URL", "http://localhost:8000").rstrip("/")

FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

SESSION_COOKIE = "swarm_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

# Per-node execution timeout (seconds); a node may override via NODE_TIMEOUT.
DEFAULT_NODE_TIMEOUT = float(os.environ.get("SWARM_NODE_TIMEOUT", "120"))

# Env vars templatable via {{ env.NAME }} must match one of these suffixes/prefixes,
# so a workflow can't exfiltrate arbitrary machine environment.
ENV_ALLOWED_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET")
ENV_ALLOWED_PREFIXES = ("SWARM_",)


def _load_secret_key() -> str:
    env = os.environ.get("SWARM_SECRET")
    if env:
        return env
    key_file = INSTANCE_DIR / "secret_key"
    if key_file.exists():
        return key_file.read_text().strip()
    key = secrets.token_hex(32)
    key_file.write_text(key)
    return key


SECRET_KEY = _load_secret_key()
