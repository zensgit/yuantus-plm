#!/usr/bin/env python3
"""
Phase 0 smoke for "Publish Released Versions to ECM" (Yuantus -> Athena).

DISCOVERY harness — it does NOT assert. It runs each step against a LIVE
Athena + Keycloak and prints raw responses so you can fill in the five
unknowns the design gates Phase 1 on:

  U1  which Athena-accepted Keycloak *realm* role permits CMIS write
      (a realm role on the service account -> realm_access.roles; NOT a client role)
  U2  the call sequence that yields a VERSIONED document
      (tested on TWO separate docs so the paths don't pollute each other)
  U3  the property key path + searchability (confirmed MANUALLY via Athena search,
      because Athena's CMIS object factory may return only CMIS/core fields)
  U4  X-Tenant-ID routing
  U5  nested createFolder  base -> Released -> <part>

Requires: python 3.10+, httpx   ->   pip install httpx
Run:
    cp .env.example .env && $EDITOR .env
    set -a; source .env; set +a
    python smoke.py
Then record findings in ../../docs/VERIFICATION_ECM_PUBLISH_PHASE0_RESULTS_TEMPLATE_20260602.md
and delete the test folder afterwards.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time

try:
    import httpx
except ImportError:
    sys.exit("missing dependency: pip install httpx")


def env(key: str, *, required: bool = True, default: str | None = None) -> str | None:
    val = os.environ.get(key, default)
    if required and not val:
        sys.exit(f"missing env {key} (see .env.example)")
    return val


KC_TOKEN_URL = env("KC_TOKEN_URL")
KC_CLIENT_ID = env("KC_CLIENT_ID")
KC_CLIENT_SECRET = env("KC_CLIENT_SECRET")
ATHENA_BROWSER = env("ATHENA_BROWSER").rstrip("/")
ATHENA_TENANT = env("ATHENA_TENANT")
BASE_FOLDER = env("ATHENA_FOLDER_ID")
PART = env("PART_NUMBER", required=False, default="P-PHASE0-0001")
RUN = time.strftime("%Y%m%d-%H%M%S")  # unique per run -> no name collisions


def show(title: str, r: "httpx.Response"):
    print(f"\n--- {title}: HTTP {r.status_code} ---")
    body = r.text or ""
    print(body[:700] + ("…" if len(body) > 700 else ""))
    try:
        return r.json()
    except Exception:
        return None


def jwt_roles(token: str):
    try:
        p = token.split(".")[1]
        p += "=" * (-len(p) % 4)
        claims = json.loads(base64.urlsafe_b64decode(p))
        return claims.get("realm_access", {}).get("roles"), claims.get("scope")
    except Exception as exc:
        return f"(decode failed: {exc})", None


def obj_id(j):
    if not j:
        return None
    o = j.get("object") or {}
    return o.get("objectId") or j.get("objectId") or (o.get("properties") or {}).get("cmis:objectId")


# Step 0 — Keycloak token (U1). DO NOT print the body: it contains access_token.
tr = httpx.post(
    KC_TOKEN_URL,
    data={"grant_type": "client_credentials",
          "client_id": KC_CLIENT_ID, "client_secret": KC_CLIENT_SECRET},
    timeout=15,
)
print(f"\n--- 0. Keycloak token: HTTP {tr.status_code} ---")
try:
    tj = tr.json()
except Exception:
    tj = None
if not tj or "access_token" not in tj:
    print("   no access_token. error/body:", (tj if tj else tr.text[:200]))
    sys.exit("fix the Keycloak client before continuing")
TOKEN = tj["access_token"]
roles, scope = jwt_roles(TOKEN)
print(f"   token_type = {tj.get('token_type')}, expires_in = {tj.get('expires_in')}")
print(f"   realm_access.roles = {roles}")
print(f"   scope = {scope}")
print("   (access_token NOT printed)")

H = {"Authorization": f"Bearer {TOKEN}", "X-Tenant-ID": ATHENA_TENANT}


def post(action: str, payload: dict):
    return httpx.post(ATHENA_BROWSER, params={"cmisaction": action}, headers=H, json=payload, timeout=30)


def get(params: dict):
    return httpx.get(ATHENA_BROWSER, params=params, headers=H, timeout=30)


def version_probe(oid, label):
    if not oid:
        print(f"   {label}: blocked (no objectId) — skip version probe")
        return
    show(f"   {label}: GET cmisselector=versions", get({"objectId": oid, "cmisselector": "versions"}))


# Step 1 — nested createFolder (U5): base -> Released-<run> -> <part>
parent = obj_id(show(f"1a. createFolder 'Released-{RUN}' under base",
                     post("createFolder", {"name": f"Released-{RUN}", "folderId": BASE_FOLDER})))
if not parent:
    print("   L1 createFolder blocked; using BASE_FOLDER as parent (note this for U5)")
    parent = BASE_FOLDER
part_folder = obj_id(show(f"1b. createFolder '{PART}' under Released-{RUN}",
                          post("createFolder", {"name": PART, "folderId": parent}))) or parent
print(f"   nested folder id = {part_folder}   (production worker uses Released/<part-number>)")

PROPS = {"plm_part": PART, "plm_rev": "A", "plm_eco": "ECO-PHASE0"}
CONTENT = base64.b64encode(b"%PDF-1.4 phase0 smoke\n").decode()

# Step 2 — U2 path A (own document): createDocument -> setContentStream
docA = obj_id(show("2A. createDocument phase0-2call (BARE keys)", post("createDocument", {
    "name": f"phase0-2call-{RUN}.pdf", "folderId": part_folder,
    "mimeType": "application/pdf", "properties": PROPS})))
if docA:
    show("2A. setContentStream", post("setContentStream", {"objectId": docA, "contentBase64": CONTENT, "majorVersion": True}))
    version_probe(docA, "U2 path A (2-call)")
else:
    print("   blocked at createDocument (path A); skip U2 path A")

# Step 3 — U2 path B (separate document): createDocument -> checkOut -> checkIn(PWC)
docB = obj_id(show("2B. createDocument phase0-3call (BARE keys)", post("createDocument", {
    "name": f"phase0-3call-{RUN}.pdf", "folderId": part_folder,
    "mimeType": "application/pdf", "properties": PROPS})))
if docB:
    pwc = obj_id(show("2B. checkOut", post("checkOut", {"objectId": docB}))) or docB
    show("2B. checkIn (content) on PWC", post("checkIn", {
        "objectId": pwc, "contentBase64": CONTENT, "majorVersion": True, "comment": "phase0"}))
    version_probe(docB, "U2 path B (3-call)")
else:
    print("   blocked at createDocument (path B); skip U2 path B")

# Step 4 — U3 read-back (CMIS may omit custom props -> searchability is a MANUAL check)
if docA:
    show("3. read-back docA (cmisselector=object) — CMIS may omit custom props", get({"objectId": docA, "cmisselector": "object"}))
print("   U3 NOTE: Athena's CMIS object factory may return only CMIS/core fields.")
print("   Confirm plm_part is searchable via Athena's Node/Search API for properties.plm_part (MANUAL).")

print(f"""
================= PHASE 0 RESULTS — record these =================
U1 realm role  : realm_access.roles above = ___ ; did Athena ACCEPT writes (2xx)? ___
                 (an Athena-accepted *realm* role on the service account — NOT a client role)
U2 version seq : path A (2-call) version count/label = ___
                 path B (3-call) version count/label = ___   -> pick the one that versions
U3 properties  : MANUAL — Athena search for properties.plm_part finds the doc? ___
U4 tenant      : everything under X-Tenant-ID='{ATHENA_TENANT}'? ___
U5 createFolder: nested Released-{RUN}/{PART} created (ids above)? ___
=> fill ../../docs/VERIFICATION_ECM_PUBLISH_PHASE0_RESULTS_TEMPLATE_20260602.md
=> then delete the test folder 'Released-{RUN}' (and cancel any checkout left by path B)
=================================================================
""")
