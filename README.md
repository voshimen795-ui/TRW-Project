# n8n + Cloudflare Tunnel

Runs [n8n](https://n8n.io) on your own computer with Docker and makes it
reachable at `https://n8n.yourdomain.com` through a Cloudflare Tunnel.
No port forwarding needed. Same setup as the course, with the tokens kept
out of GitHub.

## What lives where

- **GitHub (this repo):** the setup files. No secrets.
- **Your computer:** the `.env` file with your tokens, and `n8n-data/`
  with your workflows. Both are ignored by git.
- **Vercel:** any websites you build that call your n8n webhooks.
  n8n itself can't run on Vercel because it has to stay on all the time.

## Test mode (no domain yet)

Runs n8n only on your computer, good for learning:

```
docker compose -f docker-compose.local.yml up -d
```

Then open http://localhost:5678. Your workflows are saved in `n8n-data/`
and carry over when you switch to the full setup below.

## Full setup (with your domain)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and Python 3, and open Docker Desktop.
2. Copy `.env.example` to `.env` and fill in your Cloudflare tokens and domain.
3. Install the one Python library: `pip install -r requirements.txt`
4. Run: `python deploy_n8n.py`

When it finishes it prints your live n8n link.

## Everyday commands

- Stop n8n: `docker compose down`
- Start it again: `docker compose up -d`
- Update n8n: `docker compose pull && docker compose up -d`
- See if it's running: `docker ps`
