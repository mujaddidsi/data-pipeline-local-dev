#!/bin/bash

echo "================================================"
echo "  Kubernetes Cluster Health Check"
echo "================================================"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local description=$1
    local command=$2

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}[PASS]${NC} $description"
        ((PASS++))
    else
        echo -e "${RED}[FAIL]${NC} $description"
        ((FAIL++))
    fi
}

echo ""
echo "--- Checking Prerequisites ---"
check "Docker is running"          "docker ps"
check "Minikube is installed"      "minikube version"
check "kubectl is installed"       "kubectl version --client"
check "Helm is installed"          "helm version"

echo ""
echo "--- Checking Cluster Health ---"
check "Minikube is running"        "minikube status | grep 'host: Running'"
check "Node is Ready"              "kubectl get nodes | grep 'Ready'"
check "Namespace airflow exists"   "kubectl get namespace airflow"

echo ""
echo "--- Checking System Pods ---"
check "CoreDNS is running"         "kubectl get pods -n kube-system | grep 'coredns' | grep 'Running'"
check "API Server is running"      "kubectl get pods -n kube-system | grep 'kube-apiserver' | grep 'Running'"
check "Storage provisioner ready"  "kubectl get pods -n kube-system | grep 'storage-provisioner' | grep 'Running'"

echo ""
echo "================================================"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "================================================"

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}Cluster is healthy and ready for Part B!${NC}"
    exit 0
else
    echo -e "${RED}Some checks failed. Please fix before proceeding.${NC}"
    exit 1
fi
