## Server setup (Hostinger) — Docker dev + Cloudflare Tunnel (Option A)

This server is configured so that **apps are not exposed by host ports**. Instead, Cloudflare Tunnel routes public hostnames to **internal Docker services**.

### Goals
- **Develop as `benedikt`** using Docker/Compose.
- Expose apps via **Cloudflare hostnames** (example: `ailanguagetutor.syntagent.com`) without opening app ports to the internet.
- Keep public exposure minimal (Hostinger-friendly).

### Current security posture (high level)
- **SSH**: key-based only
  - `PermitRootLogin no`
  - `PasswordAuthentication no`
- **Firewall (UFW)**: only `22/tcp`, `80/tcp`, `443/tcp` allowed inbound.
- **Host ports**: app/db ports are **not listening on 0.0.0.0** (only SSH is public).

### Repository location
- Root copy: `/root/aiLanguageTutor`
- Working copy for development: `/home/benedikt/aiLanguageTutor`

### How to work as `benedikt`
1. SSH in as `benedikt` (SSH keys; passwords are disabled).
2. Go to the project:
   - `cd /home/benedikt/aiLanguageTutor`
3. Start/stop services:
   - **Production (recommended for the public site)**:
     - Start/update: `docker compose -f docker-compose.prod.yml up -d --build`
     - Stop: `docker compose -f docker-compose.prod.yml down`
     - Logs: `docker compose -f docker-compose.prod.yml logs -f --tail 200`
   - **Development (recommended only for local/dev access)**:
     - Start: `docker compose -f docker-compose.yml up -d`
     - Stop: `docker compose -f docker-compose.yml down`
     - Logs: `docker compose -f docker-compose.yml logs -f --tail 200`

### Switching the server stack to run from `/home/benedikt` (recommended)
The running containers should mount code and scenarios from `/home/benedikt/aiLanguageTutor` (not `/root/aiLanguageTutor`) so updates don’t require root access and MCP scenarios stay in sync.

#### 1) Move the Cloudflare token out of `/root` (so Compose can reference it)
`/root` is not accessible to `benedikt`, and Docker Compose needs to be able to reference the bind mount source path.

Create a root-owned token path under `/etc`:
- Create directory: `/etc/cloudflared`
- Copy token to: `/etc/cloudflared/tunnel-token`
- Ensure permissions: `root:root` and `600`

Then the server compose uses:
- `/etc/cloudflared/tunnel-token:/etc/cloudflared/token:ro`

#### 2) Use the server compose file
Use `docker-compose.server.yml` for the Hostinger + Cloudflare Tunnel setup:
- Start/update: `docker compose -f docker-compose.server.yml up -d --build`
- Stop: `docker compose -f docker-compose.server.yml down`
- Logs: `docker compose -f docker-compose.server.yml logs -f --tail 200`

### Why production compose is recommended even “during development”
Running the frontend with `next dev` enables hot-reload websockets and extra dev endpoints. When accessed over the public internet (Cloudflare Tunnel), this often feels slow and flaky.

Use `docker-compose.prod.yml` for `ailanguagetutor.syntagent.com`, and keep `docker-compose.yml` for local iteration.

### Cloudflare Tunnel (Option A)

#### What “Option A” means
- Services run on the Docker network, e.g.:
  - `frontend` listens on `3000` **inside Docker**
  - `backend` listens on `8000` **inside Docker**
- We do **not** publish `3000/8000/...` on the host.
- Cloudflare routes:
  - `ailanguagetutor.syntagent.com` → **tunnel** → internal service

#### Tunnel token (secret handling)
- The tunnel token is stored as a root-only file:
  - `/root/.cloudflared/tunnel-token`
- The Docker `cloudflared` container mounts it read-only.
- **Do not commit tokens into git** and do not paste them into `docker-compose.yml`.

#### Why `cloudflared` uses `network_mode: service:frontend`
The tunnel is currently **remotely managed** in Cloudflare and its ingress points to:
- `http://localhost:3000`

To make that work without publishing host ports, the `cloudflared` container shares the **frontend container network namespace**, so `localhost:3000` inside `cloudflared` resolves to the frontend service.

#### IMPORTANT: When you rebuild/recreate `frontend`, also recreate `cloudflared`
Because `cloudflared` uses `network_mode: service:frontend`, it is tied to the **specific** frontend container’s network namespace.

If you run something like:
- `docker compose -f docker-compose.server.yml up -d --build frontend`

Compose will often **recreate** the `frontend` container. In that case the tunnel may start serving **Cloudflare Tunnel Error 1033** (or 502) until you recreate `cloudflared` as well:
- `docker compose -f docker-compose.server.yml up -d --force-recreate cloudflared`

### One-command deploy helper (recommended)
To avoid forgetting the `cloudflared` recreate step, use:
- `./scripts/deploy-server`

This rebuilds/restarts `backend` + `frontend` and then force-recreates `cloudflared`.

### Cloudflare Dashboard settings (one-time)
Cloudflare Zero Trust:
- **Networks → Tunnels → (this tunnel) → Public Hostnames**
  - **Hostname**: `ailanguagetutor.syntagent.com`
  - **Service**: `http://localhost:3000`

### Verify “no public app ports”
Run on the host:
- `ss -tulpn`  → should show **only SSH (22)** publicly.
- `ufw status verbose` → should show only **22/80/443** allowed inbound.

### Adding more apps (recommended approach)
For each new app:
- Create a separate compose stack + network (or reuse a shared network).
- Do not publish ports.
- Add a new Cloudflare **Public Hostname** pointing to the target service.

If you want the cleanest multi-app routing long-term, migrate the tunnel ingress to route to **Docker service names** (e.g. `http://appX:3000`) instead of `localhost`, so `cloudflared` does not need `network_mode: service:...`.

### Fail2ban (SSH brute-force protection)
Fail2ban is installed and running with an `sshd` jail.

Useful commands:
- Check status: `fail2ban-client status` and `fail2ban-client status sshd`
- Unban an IP: `fail2ban-client set sshd unbanip <IP>`


