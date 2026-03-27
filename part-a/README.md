# Part A — Local Kubernetes Bootstrap

## Tool Choice: Minikube

Minikube was chosen because:
- Simple single-command setup with Docker driver
- Works seamlessly with WSL2 + Docker Engine
- Built-in addons (ingress, metrics-server, storage-provisioner)
- Well-documented and widely used for local development

## Prerequisites

- WSL2 (Ubuntu 22.04)
- Docker Engine installed and running
- Minimum 4GB RAM, 2 CPUs available

Install required tools:
```bash
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

## Quick Start
```bash
# Option 1 — One command setup
./setup.sh

# Option 2 — Using Makefile
make cluster-up
```

## Makefile Commands

| Command | Description |
|---|---|
| `make cluster-up` | Start minikube cluster + create airflow namespace |
| `make cluster-down` | Stop minikube cluster |
| `make status` | Check cluster and namespace status |
| `make healthcheck` | Run health check script |

## Verify Cluster
```bash
# Check node is ready
kubectl get nodes

# Check airflow namespace exists
kubectl get namespace airflow

# Run full health check
make healthcheck
```

## Expected Output
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   Xd    v1.35.0
```
```
NAME      STATUS   AGE
airflow   Active   Xs
```
