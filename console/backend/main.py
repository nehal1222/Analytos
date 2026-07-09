"""Console backend: dashboard reads + HITL review actions.

Two logical surfaces sharing one FastAPI app (kept together deliberately,
to avoid running/duplicating two near-identical services for a POC):

- `/api/{products,features,proof-points,decisions,icp-segments,personas,
  email-threads,people,search,commits,branches}` -- the dashboard's read
  layer. Reads `main` as the `act-admin` actor. Gated behind
  `auth.current_user` (any logged-in role) -- see auth.py.
- `/api/runs/...` -- the HITL review queue: list pending ingestion runs,
  view a run's diff against main, approve (merge) or reject (discard).
  Gated behind `auth.require_role("admin", "reviewer")`. The reviewer
  identity for the resulting merge/branch-delete comes from the
  *authenticated session's* `actor_id` (auth.py, verified server-side at
  login), never from anything the client's request body claims -- that's
  the actual fix for "commit attribution is real," not just "the UI has a
  name field."

Login accounts are provisioned with `manage_users.py`, not created here.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))

from fastapi import Depends, FastAPI, HTTPException, Response  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import auth  # noqa: E402
import diff as diff_mod  # noqa: E402
from omnigraph_client import OmniGraphError, client_for  # noqa: E402

app = FastAPI(title="Analytos Context Layer Console")

# Cookie-based sessions require `allow_credentials=True`, which the CORS
# spec forbids pairing with a wildcard origin -- browsers will silently
# refuse to attach the cookie. FRONTEND_ORIGIN must be the dashboard's real
# origin (comma-separated for more than one).
FRONTEND_ORIGINS = os.environ.get("FRONTEND_ORIGIN", "http://127.0.0.1:5173").split(",")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
# Local dev proxies the frontend and backend behind the same origin (Vite's
# proxy in vite.config.js), so the cookie is same-site there and "strict"
# is correct and safest. Hosted, the frontend (Netlify) and backend
# (Render) are different domains -- a genuinely cross-site request -- and
# SameSite=Strict/Lax cookies are never sent cross-site at all, silently
# breaking login. SameSite=None (requires Secure) is the only setting that
# works cross-site, so it must be opt-in per deployment, not the default.
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "strict")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    auth.init_db()


ADMIN = client_for("act-admin")
RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline" / "runs"


@app.get("/")
def root():
    # This is an API-only backend (the dashboard UI is the separate Vite
    # dev server / static build) -- point anyone hitting it directly at
    # something useful instead of a bare 404.
    return {
        "service": "Analytos Context Layer Console API",
        "docs": "/docs",
        "dashboard": "http://127.0.0.1:5173",
    }


# ---- auth -----------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str
    display_name: str


@app.post("/api/auth/signup")
def signup(body: SignupRequest, response: Response):
    # Self-service is scoped to "viewer" (read-only) accounts only --
    # "reviewer" needs a real Cedar actor wired into cluster/base.policy.yaml
    # and tokens.dev.json, which a signup form can't safely provision on
    # its own; that stays a deliberate CLI action (manage_users.py). This
    # still gets a recruiter/evaluator into the dashboard immediately,
    # without a round-trip to whoever runs the CLI.
    username = body.username.strip().lower()
    if not username or not username.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "username must be alphanumeric (- and _ allowed)")
    if len(body.password) < 8:
        raise HTTPException(400, "password must be at least 8 characters")
    if not body.display_name.strip():
        raise HTTPException(400, "display name is required")
    if auth.user_exists(username):
        raise HTTPException(409, f"username '{username}' is already taken")

    auth.create_user(username, body.password, body.display_name.strip(), "viewer", None)
    user = auth.verify_password(username, body.password)
    token = auth.create_session_token(user)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=auth.SESSION_TTL_SECONDS,
    )
    return {"username": user.username, "display_name": user.display_name, "role": user.role}


@app.post("/api/auth/login")
def login(body: LoginRequest, response: Response):
    user = auth.verify_password(body.username, body.password)
    if user is None:
        raise HTTPException(401, "invalid username or password")
    token = auth.create_session_token(user)
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=auth.SESSION_TTL_SECONDS,
    )
    return {"username": user.username, "display_name": user.display_name, "role": user.role}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(auth.SESSION_COOKIE)
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: auth.User = Depends(auth.current_user)):
    return {"username": user.username, "display_name": user.display_name, "role": user.role}


def q(name: str, params: dict | None = None, branch: str | None = None) -> dict:
    try:
        return ADMIN.invoke_query(name, params or {}, branch=branch)
    except OmniGraphError as e:
        raise HTTPException(status_code=e.status, detail=e.payload) from e


# ---- dashboard reads ------------------------------------------------------

@app.get("/api/products", dependencies=[Depends(auth.current_user)])
def list_products():
    return q("list_products")["rows"]


@app.get("/api/products/{slug}", dependencies=[Depends(auth.current_user)])
def get_product(slug: str):
    rows = q("get_product", {"slug": slug})["rows"]
    if not rows:
        raise HTTPException(404, "product not found")
    features = q("list_features_for_product", {"slug": slug})["rows"]
    for f in features:
        f["proof_points"] = q("list_proof_points_for_feature", {"slug": f["slug"]})["rows"]
    return {
        "product": rows[0],
        "features": features,
        "proof_points": q("list_proof_points_for_product", {"slug": slug})["rows"],
        "decisions": q("list_decisions_for_product", {"slug": slug})["rows"],
        "segments": q("list_segments_for_product", {"slug": slug})["rows"],
    }


@app.get("/api/features", dependencies=[Depends(auth.current_user)])
def list_features():
    return q("list_all_features")["rows"]


@app.get("/api/proof-points", dependencies=[Depends(auth.current_user)])
def list_proof_points():
    return q("list_all_proof_points")["rows"]


@app.get("/api/decisions", dependencies=[Depends(auth.current_user)])
def list_decisions():
    return q("list_decisions")["rows"]


@app.get("/api/icp-segments", dependencies=[Depends(auth.current_user)])
def list_icp_segments():
    return q("list_icp_segments")["rows"]


@app.get("/api/icp-segments/{slug}", dependencies=[Depends(auth.current_user)])
def get_icp_segment(slug: str):
    rows = q("get_icp_segment", {"slug": slug})["rows"]
    if not rows:
        raise HTTPException(404, "segment not found")
    return {"segment": rows[0], "personas": q("list_personas_for_segment", {"slug": slug})["rows"]}


@app.get("/api/personas", dependencies=[Depends(auth.current_user)])
def list_personas():
    return q("list_personas")["rows"]


@app.get("/api/email-threads", dependencies=[Depends(auth.current_user)])
def list_email_threads():
    return q("list_email_threads")["rows"]


@app.get("/api/email-threads/{slug}", dependencies=[Depends(auth.current_user)])
def get_email_thread(slug: str):
    rows = q("get_email_thread", {"slug": slug})["rows"]
    if not rows:
        raise HTTPException(404, "thread not found")
    return {"thread": rows[0], "participants": q("list_participants_for_thread", {"slug": slug})["rows"]}


@app.get("/api/people", dependencies=[Depends(auth.current_user)])
def list_people():
    return q("list_people")["rows"]


@app.get("/api/search", dependencies=[Depends(auth.current_user)])
def search(query_text: str):
    params = {"q": query_text}
    return {
        "products": q("search_products", params)["rows"],
        "features": q("search_features", params)["rows"],
        "proof_points": q("search_proof_points", params)["rows"],
        "decisions": q("search_decisions", params)["rows"],
        "icp_segments": q("search_icp_segments", params)["rows"],
    }


@app.get("/api/commits", dependencies=[Depends(auth.current_user)])
def commits(branch: str = "main"):
    return ADMIN.commits(branch=branch)


@app.get("/api/branches", dependencies=[Depends(auth.current_user)])
def branches():
    return ADMIN.branch_list()


# ---- HITL review -----------------------------------------------------

def _load_manifest(run_id: str) -> dict:
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(404, "run not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(run_id: str, manifest: dict) -> None:
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


@app.get("/api/runs", dependencies=[Depends(auth.current_user)])
def list_runs():
    if not RUNS_DIR.exists():
        return []
    runs = []
    for f in sorted(RUNS_DIR.glob("*.json"), reverse=True):
        m = json.loads(f.read_text(encoding="utf-8"))
        runs.append(
            {
                "run_id": m["run_id"],
                "branch": m["branch"],
                "created_at": m["created_at"],
                "actor": m["actor"],
                "source_docs": m["source_docs"],
                "node_counts": m["node_counts"],
                "edge_counts": m["edge_counts"],
                "warnings": m.get("warnings", []),
                "status": m["status"],
                "approved_by": m.get("approved_by"),
                "approved_at": m.get("approved_at"),
                "approved_comment": m.get("approved_comment"),
                "rejected_by": m.get("rejected_by"),
                "rejected_at": m.get("rejected_at"),
                "rejected_comment": m.get("rejected_comment"),
            }
        )
    return runs


@app.get("/api/runs/{run_id}", dependencies=[Depends(auth.current_user)])
def get_run(run_id: str):
    return _load_manifest(run_id)


@app.get("/api/runs/{run_id}/diff", dependencies=[Depends(auth.current_user)])
def run_diff(run_id: str):
    manifest = _load_manifest(run_id)
    return diff_mod.compute_diff(manifest, ADMIN)


class ReviewComment(BaseModel):
    # Optional rationale a reviewer leaves alongside their decision -- not
    # required by the engine's governance model (that only needs *who*
    # merged), but a real reviewer's job includes explaining *why*, and
    # without a place to put that, "review" is just a rubber stamp.
    comment: str | None = None


@app.post("/api/runs/{run_id}/approve")
def approve_run(
    run_id: str,
    body: ReviewComment,
    user: auth.User = Depends(auth.require_role("admin", "reviewer")),
):
    manifest = _load_manifest(run_id)
    if manifest["status"] != "pending_review":
        raise HTTPException(400, f"run is already {manifest['status']}")
    # The actor performing this merge is whatever the *verified session*
    # maps to -- not a request-body field a client could set to anyone.
    actor = user.actor_id
    if not actor:
        raise HTTPException(400, f"account '{user.username}' has no Cedar actor mapped -- can't approve/merge")

    client = client_for(actor)
    try:
        merge_result = client.branch_merge(source=manifest["branch"], target="main")
    except OmniGraphError as e:
        raise HTTPException(status_code=e.status, detail=e.payload) from e

    try:
        client.branch_delete(manifest["branch"])
    except OmniGraphError as e:
        # Branch cleanup is best-effort -- the merge already landed and is
        # what matters for governance. Logged (not silently swallowed) so a
        # persistently undeleted branch is visible rather than a mystery.
        print(f"branch cleanup failed for '{manifest['branch']}': {e.status} {e.payload}")

    manifest["status"] = "merged"
    manifest["approved_by"] = actor
    manifest["approved_at"] = datetime.now(timezone.utc).isoformat()
    manifest["approved_comment"] = body.comment or None
    manifest["merge_result"] = merge_result
    _save_manifest(run_id, manifest)
    return manifest


@app.post("/api/runs/{run_id}/reject")
def reject_run(
    run_id: str,
    body: ReviewComment,
    user: auth.User = Depends(auth.require_role("admin", "reviewer")),
):
    manifest = _load_manifest(run_id)
    if manifest["status"] != "pending_review":
        raise HTTPException(400, f"run is already {manifest['status']}")
    actor = user.actor_id
    if not actor:
        raise HTTPException(400, f"account '{user.username}' has no Cedar actor mapped -- can't reject")

    client = client_for(actor)
    try:
        client.branch_delete(manifest["branch"])
    except OmniGraphError as e:
        raise HTTPException(status_code=e.status, detail=e.payload) from e

    manifest["status"] = "rejected"
    manifest["rejected_by"] = actor
    manifest["rejected_at"] = datetime.now(timezone.utc).isoformat()
    manifest["rejected_comment"] = body.comment or None
    _save_manifest(run_id, manifest)
    return manifest


SEED_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "seed-data"


@app.get("/api/source-docs/{filename}", dependencies=[Depends(auth.current_user)])
def get_source_doc(filename: str):
    # A reviewer approving/rejecting an extraction can only judge it
    # faithfully if they can see the actual source text, not just the
    # structured output -- this is what makes "review" mean something.
    # Path(filename).name strips any directory components, so this can
    # only ever resolve to a file directly inside seed-data/.
    safe_name = Path(filename).name
    path = SEED_DATA_DIR / safe_name
    if not safe_name.endswith(".md") or not path.is_file():
        raise HTTPException(404, "source document not found")
    return {"filename": safe_name, "text": path.read_text(encoding="utf-8")}


class IngestRequest(BaseModel):
    filename: str
    content: str


PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline"


@app.post("/api/ingest", dependencies=[Depends(auth.current_user)])
def ingest_document(body: IngestRequest):
    # Any logged-in role can submit a document -- this only ever creates a
    # pending review branch (see ingest.py: it never touches main), so it
    # doesn't bypass the human-approval gate. Merging still requires
    # admin/reviewer, enforced separately in approve_run.
    safe_name = Path(body.filename).name
    if not safe_name.endswith(".md"):
        raise HTTPException(400, "filename must end in .md")
    if not body.content.strip():
        raise HTTPException(400, "content is empty")

    dest = SEED_DATA_DIR / safe_name
    if dest.exists():
        raise HTTPException(
            409,
            f"'{safe_name}' already exists in seed-data/ -- choose a different filename "
            "rather than overwriting existing source material",
        )

    dest.write_text(body.content, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, str(PIPELINE_DIR / "ingest.py"), str(dest)],
            cwd=PIPELINE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as e:
        raise HTTPException(504, "ingestion pipeline timed out") from e

    if result.returncode != 0:
        # The file is already written -- leave it in place (it's real
        # source material now, same as any other seed doc) but surface the
        # pipeline's own error output rather than a bare exit code.
        raise HTTPException(500, f"ingestion failed:\n{result.stdout}\n{result.stderr}")

    return {"filename": safe_name, "output": result.stdout}
