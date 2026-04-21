#!/bin/bash
# setup.sh — One-command cluster bootstrap

set -e

echo "================================================"
echo "  Local Data Pipeline — Cluster Bootstrap"
echo "================================================"

# Step 1 — Cek prerequisites
echo "[1/4] Checking prerequisites..."
command -v docker   || { echo "Docker not found!"; exit 1; }
command -v minikube || { echo "Minikube not found!"; exit 1; }
command -v kubectl  || { echo "kubectl not found!"; exit 1; }
command -v helm     || { echo "Helm not found!"; exit 1; }
echo "Prerequisites OK!"

# Step 2 — Start minikube
echo "[2/4] Starting minikube cluster..."
minikube start --driver=docker --memory=4096 --cpus=2

# Step 3 — Create namespace
echo "[3/4] Creating airflow namespace..."
kubectl create namespace airflow --dry-run=client -o yaml | kubectl apply -f -

# Step 4 — Verify
echo "[4/4] Verifying cluster..."
kubectl get nodes
kubectl get namespace airflow

echo ""
echo "================================================"
echo "  Cluster is ready! Run 'make healthcheck'"
echo "  to verify before proceeding to Part B."
echo "================================================"
