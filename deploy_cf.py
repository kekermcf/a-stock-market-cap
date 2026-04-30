"""
Cloudflare Pages Deployment Script v2
Correct API flow: create deployment → get upload URL → upload → signal completion
"""
import requests
import os
import json
import sys

CF_TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
if not CF_TOKEN:
    print("ERROR: No Cloudflare API token")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {CF_TOKEN}",
    "Content-Type": "application/json"
}

BASE_URL = "https://api.cloudflare.com/client/v4"
PROJECT_NAME = "stock-keke"
DOMAIN = "stock-keke.com"
INDEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

print(f"Token: {CF_TOKEN[:12]}...")
print(f"File: {INDEX_FILE} ({os.path.getsize(INDEX_FILE):,} bytes)")

def cf_get(path):
    r = requests.get(f"{BASE_URL}{path}", headers=HEADERS, timeout=30)
    return r.json()

def cf_post(path, data=None):
    r = requests.post(f"{BASE_URL}{path}", headers=HEADERS, json=data or {}, timeout=30)
    return r.json()

def cf_delete(path):
    r = requests.delete(f"{BASE_URL}{path}", headers=HEADERS, timeout=30)
    return r.json()

# Step 1: Get Account ID
print("\n=== Step 1: Account ID ===")
accounts = cf_get("/accounts")
if not accounts.get("success"):
    print(f"ERROR: {json.dumps(accounts, indent=2)[:500]}")
    sys.exit(1)
account_id = accounts["result"][0]["id"]
print(f"  {account_id}")

# Step 2: Get Pages project
print(f"\n=== Step 2: Get/Create project '{PROJECT_NAME}' ===")
pages = cf_get(f"/accounts/{account_id}/pages/projects")
existing_name = None
if pages.get("success"):
    for p in pages["result"]:
        print(f"  Found project: {p['name']}")
        if p["name"] == PROJECT_NAME:
            existing_name = p["name"]

if existing_name:
    print(f"  Using existing project: {existing_name}")
else:
    print(f"  Creating project...")
    create = cf_post(f"/accounts/{account_id}/pages/projects", {
        "name": PROJECT_NAME,
        "production_branch": "main"
    })
    if create.get("success"):
        existing_name = create["result"]["name"]
        print(f"  Created: {existing_name}")
    else:
        print(f"  ERROR: {json.dumps(create, indent=2)[:500]}")
        sys.exit(1)

# Step 3: Create deployment (get upload URL)
print(f"\n=== Step 3: Create deployment ===")
deploy = cf_post(f"/accounts/{account_id}/pages/projects/{existing_name}/deployments")
if not deploy.get("success"):
    print(f"  ERROR: {json.dumps(deploy, indent=2)[:500]}")
    sys.exit(1)

deployment_id = deploy["result"]["id"]
upload_url = deploy["result"].get("upload_url", "")
staging_domain = deploy["result"].get("staging_domain", "")
print(f"  Deployment ID: {deployment_id}")
print(f"  Upload URL: {upload_url[:80]}...")
print(f"  Staging: {staging_domain}")

# Step 4: Upload file
print(f"\n=== Step 4: Upload index.html ===")
with open(INDEX_FILE, "rb") as f:
    files = {"index.html": ("index.html", f, "text/html; charset=utf-8")}
    # Upload URL doesn't need auth header - it's pre-signed
    upload_resp = requests.post(upload_url, files=files, timeout=60)
    print(f"  Status: {upload_resp.status_code}")
    print(f"  Response: {upload_resp.text[:200]}")

# Step 5: Signal completion
print(f"\n=== Step 5: Signal completion ===")
# Send _finished flag (empty file signals completion)
finish_files = {"_finished": ("_finished", b"true", "text/plain")}
finish_resp = requests.post(upload_url, files=finish_files, timeout=30)
print(f"  Status: {finish_resp.status_code}")
print(f"  Response: {finish_resp.text[:200]}")

# Wait a moment for deployment to start processing
import time
print("\n=== Step 6: Check deployment status ===")
for i in range(10):
    time.sleep(3)
    status = cf_get(f"/accounts/{account_id}/pages/projects/{existing_name}/deployments/{deployment_id}")
    if status.get("success"):
        s = status["result"]
        stage = s.get("latest_stage", {}).get("name", "unknown")
        dc_status = s.get("latest_stage", {}).get("status", "unknown")
        print(f"  [{i+1}] Stage: {stage}, Status: {dc_status}")
        if stage == "deploy" and dc_status == "success":
            print("  ✅ Deployment successful!")
            break
        if stage == "deploy" and dc_status == "failure":
            print(f"  ❌ Deployment failed!")
            print(f"  Details: {json.dumps(s, indent=2)[:500]}")
            break
    else:
        print(f"  Status check error: {status}")
        break

# Step 7: Bind custom domain
print(f"\n=== Step 7: Custom domain '{DOMAIN}' ===")
domains = cf_get(f"/accounts/{account_id}/pages/projects/{existing_name}/domains")
domain_bound = False
if domains.get("success"):
    for d in domains["result"]:
        if d["name"] == DOMAIN:
            domain_bound = True
            print(f"  ✅ Domain already bound: {DOMAIN}")
            break

if not domain_bound:
    print(f"  Binding {DOMAIN}...")
    add = cf_post(f"/accounts/{account_id}/pages/projects/{existing_name}/domains", {"name": DOMAIN})
    if add.get("success"):
        print(f"  ✅ Domain bound: {DOMAIN}")
    else:
        print(f"  ⚠️  Error: {json.dumps(add, indent=2)[:300]}")

# Step 8: Purge cache
print(f"\n=== Step 8: Purge cache ===")
zones = cf_get(f"/zones?name={DOMAIN}")
if zones.get("success") and zones["result"]:
    zone_id = zones["result"][0]["id"]
    purge = cf_post(f"/zones/{zone_id}/purge_cache", {"purge_everything": True})
    print(f"  Purge: {purge.get('success')}")
else:
    print(f"  Zone not found, trying account-level purge...")
    # Try to purge by hostname
    purge_headers = dict(HEADERS)
    purge_headers["Content-Type"] = "application/json"
    purge = requests.post(
        f"{BASE_URL}/accounts/{account_id}/cache/purge",
        headers=purge_headers,
        json={"hosts": [DOMAIN]},
        timeout=30
    )
    print(f"  Account purge: {purge.json().get('success')}")

# Step 9: Verify
print(f"\n=== Step 9: Verify deployment ===")
time.sleep(2)
verify = requests.get(f"https://{staging_domain}" if staging_domain else f"https://{DOMAIN}", 
                       headers={"User-Agent": "WorkBuddy/1.0"}, timeout=15)
print(f"  Status: {verify.status_code}")
# Check for key features in the response
content = verify.text
has_ah_filter = 'ahFilter' in content
has_goto = 'gotoInput' in content
has_mv_label = 'page-mv-label' in content or 'pageMv' in content
print(f"  A+H Filter: {'✅' if has_ah_filter else '❌'}")
print(f"  Page Jump Input: {'✅' if has_goto else '❌'}")
print(f"  Page MV Labels: {'✅' if has_mv_label else '❌'}")

print(f"\n{'='*50}")
print(f"Your site: https://{DOMAIN}")
print(f"Staging: https://{staging_domain}" if staging_domain else "")
print(f"Done!")
