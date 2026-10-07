"""
Sets up n8n with a Cloudflare Tunnel, same steps as the course script,
but reads your tokens from the .env file instead of keeping them in code.

Run from this folder:  python deploy_n8n.py
"""
import base64
import os
import subprocess
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
API = "https://api.cloudflare.com/client/v4"


def read_env(path):
    values = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_values(path, updates):
    """Set keys in .env, keeping everything else as it is."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    remaining = dict(updates)
    for i, line in enumerate(lines):
        key = line.split("=", 1)[0].strip()
        if key in remaining and not line.lstrip().startswith("#"):
            lines[i] = f"{key}={remaining.pop(key)}"
    for key, value in remaining.items():
        lines.append(f"{key}={value}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def fail(message, details=None):
    print(f"❌ {message}")
    if details is not None:
        print("   ", details)
    sys.exit(1)


if not os.path.exists(ENV_PATH):
    fail("No .env file found. Copy .env.example to .env and fill in your tokens.")

env = read_env(ENV_PATH)
ACCOUNT_TOKEN = env.get("CLOUDFLARE_ACCOUNT_TOKEN", "")
DNS_TOKEN = env.get("CLOUDFLARE_DNS_TOKEN", "")
DOMAIN = env.get("DOMAIN", "")
SUBDOMAIN = env.get("SUBDOMAIN", "")

missing = [k for k, v in {
    "CLOUDFLARE_ACCOUNT_TOKEN": ACCOUNT_TOKEN,
    "CLOUDFLARE_DNS_TOKEN": DNS_TOKEN,
    "DOMAIN": DOMAIN,
}.items() if not v or v == "example.com"]
if missing:
    fail("Please fill these in your .env file: " + ", ".join(missing))

FULL_HOSTNAME = f"{SUBDOMAIN}.{DOMAIN}" if SUBDOMAIN else DOMAIN
TUNNEL_NAME = f"n8n-tunnel-{SUBDOMAIN}" if SUBDOMAIN else "n8n-tunnel"

account_headers = {"Authorization": f"Bearer {ACCOUNT_TOKEN}", "Content-Type": "application/json"}
dns_headers = {"Authorization": f"Bearer {DNS_TOKEN}", "Content-Type": "application/json"}

print(f"🚀 Starting automated deployment for {FULL_HOSTNAME}...\n")

# 1. Account ID
print("1/6 Fetching Cloudflare Account ID...")
acc_res = requests.get(f"{API}/accounts", headers=account_headers).json()
if not acc_res.get("success") or not acc_res.get("result"):
    fail("Failed to get Account ID. Check CLOUDFLARE_ACCOUNT_TOKEN permissions:", acc_res)
account_id = acc_res["result"][0]["id"]
print(f"   ✓ Account ID: {account_id}")

# 2. Zone ID
print(f"2/6 Fetching Cloudflare Zone ID for {DOMAIN}...")
zone_res = requests.get(f"{API}/zones", params={"name": DOMAIN}, headers=dns_headers).json()
if not zone_res.get("success") or not zone_res.get("result"):
    fail(f"Failed to get Zone ID for {DOMAIN}. Check CLOUDFLARE_DNS_TOKEN permissions:", zone_res)
zone_id = zone_res["result"][0]["id"]
print(f"   ✓ Zone ID: {zone_id}")

# 3. Create or reuse the tunnel
print(f"3/6 Creating Cloudflare Tunnel '{TUNNEL_NAME}'...")
r_list = requests.get(
    f"{API}/accounts/{account_id}/cfd_tunnel",
    params={"name": TUNNEL_NAME, "is_deleted": "false"},
    headers=account_headers,
).json()
if r_list.get("success") and r_list.get("result"):
    tunnel_id = r_list["result"][0]["id"]
    print(f"   ✓ Found existing Tunnel ID: {tunnel_id}")
else:
    tunnel_secret = base64.b64encode(os.urandom(32)).decode("utf-8")
    r_create = requests.post(
        f"{API}/accounts/{account_id}/cfd_tunnel",
        headers=account_headers,
        json={"name": TUNNEL_NAME, "tunnel_secret": tunnel_secret, "config_src": "cloudflare"},
    ).json()
    if not r_create.get("success"):
        fail("Could not create tunnel:", r_create)
    tunnel_id = r_create["result"]["id"]
    print(f"   ✓ Created new Tunnel ID: {tunnel_id}")

r_token = requests.get(
    f"{API}/accounts/{account_id}/cfd_tunnel/{tunnel_id}/token",
    headers=account_headers,
).json()
if not r_token.get("success"):
    fail("Failed to get Tunnel Token:", r_token)
tunnel_token = r_token["result"]

# 4. Route the hostname to n8n
print(f"4/6 Configuring Ingress -> Route {FULL_HOSTNAME} to n8n:5678...")
r_ingress = requests.put(
    f"{API}/accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations",
    headers=account_headers,
    json={"config": {"ingress": [
        {"hostname": FULL_HOSTNAME, "service": "http://n8n:5678"},
        {"service": "http_status:404"},
    ]}},
).json()
if not r_ingress.get("success"):
    fail("Failed to set Ingress config:", r_ingress)
print("   ✓ Ingress configuration updated successfully.")

# 5. DNS CNAME
print(f"5/6 Pointing DNS CNAME for {FULL_HOSTNAME}...")
cname_target = f"{tunnel_id}.cfargotunnel.com"
dns_payload = {"type": "CNAME", "name": FULL_HOSTNAME, "content": cname_target, "proxied": True, "ttl": 1}
dns_list = requests.get(
    f"{API}/zones/{zone_id}/dns_records",
    params={"name": FULL_HOSTNAME, "type": "CNAME"},
    headers=dns_headers,
).json()
if dns_list.get("result"):
    record_id = dns_list["result"][0]["id"]
    r_dns = requests.put(f"{API}/zones/{zone_id}/dns_records/{record_id}", headers=dns_headers, json=dns_payload).json()
else:
    r_dns = requests.post(f"{API}/zones/{zone_id}/dns_records", headers=dns_headers, json=dns_payload).json()
if not r_dns.get("success"):
    fail("Failed to set DNS record:", r_dns)
print(f"   ✓ DNS CNAME pointing to {cname_target}")

# 6. Save tunnel token to .env and start Docker
print("6/6 Saving settings and launching Docker...")
write_env_values(ENV_PATH, {"N8N_HOST": FULL_HOSTNAME, "TUNNEL_TOKEN": tunnel_token})
os.makedirs(os.path.join(HERE, "n8n-data"), exist_ok=True)
print("   ✓ .env updated (tunnel token saved locally, not in GitHub).")
print("   🚀 Running `docker compose up -d`...")
subprocess.run(["docker", "compose", "up", "-d"], cwd=HERE, check=True)

print("\n" + "=" * 50)
print("🎉 n8n IS LIVE AND READY AT:")
print(f"👉 https://{FULL_HOSTNAME}")
print("=" * 50)
