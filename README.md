# K8S Microservice — Docker · Helm · Kubernetes · ArgoCD · CI/CD

A self-contained reference implementation of a cloud-native microservice and a
full **GitOps** delivery pipeline. A FastAPI service is containerized with
Docker, packaged with Helm, deployed to Kubernetes, continuously delivered with
ArgoCD, and built/released automatically by GitHub Actions.

> The defining property of this project: **a single `git push` deploys to the
> cluster, with no manual `docker`, `helm`, or `kubectl` commands.**

---

## Architecture

```
   Developer                GitHub Actions (CI)              Git repo
  ┌──────────┐   git push   ┌─────────────────────┐  commit  ┌──────────────┐
  │  app/**  │ ───────────▶ │ 1. build image      │ ───────▶ │ chart/       │
  │  change  │              │ 2. push to GHCR      │  (tag    │ values.yaml  │
  └──────────┘              │ 3. bump image tag    │   bump)  │ (new tag)    │
                            └─────────────────────┘          └──────┬───────┘
                                       │ push image                  │ watches
                                       ▼                             ▼
                            ┌─────────────────────┐          ┌──────────────┐
                            │  GHCR (registry)    │ ◀─ pull ─ │   ArgoCD     │
                            └─────────────────────┘          │   (CD)       │
                                                             └──────┬───────┘
                                                                    │ sync
                                                                    ▼
                                                          ┌──────────────────┐
                                                          │ Kubernetes        │
                                                          │ Deployment +      │
                                                          │ Service (pods)    │
                                                          └──────────────────┘
```

**The flow:** push code → CI builds and pushes the image to GHCR → CI rewrites
the image tag in `chart/values.yaml` and commits it back → ArgoCD detects the
commit and syncs the cluster to match Git. Git is the single source of truth.

---

## Tech stack

| Concern              | Tool                          |
|----------------------|-------------------------------|
| Service / API        | Python 3.12 · FastAPI · Uvicorn |
| Containerization     | Docker                        |
| Packaging            | Helm 3                        |
| Orchestration        | Kubernetes (Minikube locally) |
| Continuous Delivery  | ArgoCD (GitOps)               |
| Continuous Integration | GitHub Actions              |
| Container registry   | GitHub Container Registry (GHCR) |

---

## Project structure

```
k8s-microservice/
├── app/
│   ├── __init__.py
│   ├── config.py            # config loaded from environment variables
│   └── main.py              # FastAPI app + endpoints
├── chart/                   # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml          # default values (image tag bumped by CI)
│   ├── values-dev.yaml      # dev environment override
│   ├── values-prod.yaml     # prod environment override
│   └── templates/
│       ├── _helpers.tpl
│       ├── deployment.yaml
│       └── service.yaml
├── argocd/
│   └── application.yaml     # ArgoCD Application (points to chart/ in this repo)
├── .github/workflows/
│   └── ci-cd.yaml           # build → push → tag bump → commit-back pipeline
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── README.md
```

---

## API reference

| Method | Path              | Description                                  |
|--------|-------------------|----------------------------------------------|
| GET    | `/`               | Service metadata (name, version, environment)|
| GET    | `/health`         | Liveness probe — is the process alive?       |
| GET    | `/ready`          | Readiness probe — ready to serve traffic?    |
| GET    | `/api/items`      | List all items                               |
| POST   | `/api/items`      | Create an item (`{"name", "description"}`)   |
| GET    | `/api/items/{id}` | Fetch a single item                          |
| GET    | `/docs`           | Auto-generated interactive Swagger UI        |

The `/health` and `/ready` endpoints exist specifically so Kubernetes can run
liveness and readiness probes against the pods.

---

## Configuration

All runtime config comes from environment variables (12-factor style), which is
what lets Helm change behavior per environment without code changes.

| Variable      | Default              | Purpose                          |
|---------------|----------------------|----------------------------------|
| `APP_NAME`    | `k8s-microservice`   | Service name                     |
| `APP_VERSION` | `1.0.0`              | Reported version                 |
| `APP_ENV`     | `local`              | Environment label (local/dev/prod)|
| `PORT`        | `8000`               | Port the server binds to         |
| `LOG_LEVEL`   | `info`               | Log level                        |

Helm injects these from the `env:` block in the values files. Override per
environment with `values-dev.yaml` / `values-prod.yaml`.

---

## Running it

### 1. Local development

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# visit http://localhost:8000/docs
```

### 2. Docker

```bash
docker build -t k8s-microservice:1.0.0 .
docker run -d -p 8000:8000 --name microservice k8s-microservice:1.0.0
curl http://localhost:8000/health
```

### 3. Kubernetes via Helm (manual)

```bash
minikube start --driver=docker --cpus=2 --memory=4096
minikube image load k8s-microservice:1.0.0
helm lint ./chart
helm install microservice ./chart -n microservice --create-namespace
# deploy to a specific environment instead:
helm upgrade microservice ./chart -n microservice -f chart/values-dev.yaml
```

### 4. GitOps with ArgoCD

```bash
# install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# admin password for the UI
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 --decode; echo

# open the dashboard
kubectl port-forward svc/argocd-server -n argocd 8081:443   # https://localhost:8081

# register the application (edit repoURL first)
kubectl apply -f argocd/application.yaml
```

ArgoCD then continuously syncs the cluster to match `chart/` on the `main`
branch (`prune` + `selfHeal` enabled).

### 5. CI/CD

On every push to `main` touching `app/**`, `requirements.txt`, `Dockerfile`, or
the workflow file, GitHub Actions builds and pushes the image to GHCR, rewrites
the image tag in `chart/values.yaml`, and commits it back. ArgoCD picks up that
commit and rolls out the new version automatically.

**One-time setup:** in the repo, set *Settings → Actions → General → Workflow
permissions* to **Read and write**, and after the first run mark the GHCR
package **Public** so the cluster can pull it.

---

## Testing the running service

```bash
kubectl port-forward -n microservice svc/microservice-microservice 8080:80
curl http://localhost:8080/health
curl http://localhost:8080/
curl -X POST http://localhost:8080/api/items \
  -H "Content-Type: application/json" \
  -d '{"name":"demo","description":"hello k8s"}'
```

---

## Troubleshooting

| Symptom                              | Cause / fix                                                        |
|--------------------------------------|--------------------------------------------------------------------|
| `ImagePullBackOff` (local Helm)      | `minikube image load k8s-microservice:1.0.0`                       |
| `ImagePullBackOff` (after CI)        | GHCR package is private → make it Public                           |
| ArgoCD `ComparisonError`             | Wrong `repoURL` or private repo → fix URL / make repo public       |
| App stuck `OutOfSync`                | Click **Sync** once in the ArgoCD UI                               |
| CI commit-back fails with 403        | Set Workflow permissions to Read and write                        |
| Workflow didn't trigger              | Only `chart/**` changed — excluded by design to avoid a loop      |
