.PHONY: cluster-up cluster-down status healthcheck help

help:
	@echo "Available commands:"
	@echo "  make cluster-up    - Start minikube cluster"
	@echo "  make cluster-down  - Stop minikube cluster"
	@echo "  make status        - Check cluster status"
	@echo "  make healthcheck   - Run health check script"

cluster-up:
	@echo "Starting minikube cluster..."
	minikube start --driver=docker --memory=4096 --cpus=2
	kubectl create namespace airflow --dry-run=client -o yaml | kubectl apply -f -
	@echo "Cluster is up!"

cluster-down:
	@echo "Stopping minikube cluster..."
	minikube stop
	@echo "Cluster stopped."

status:
	@echo "=== Minikube Status ==="
	minikube status
	@echo ""
	@echo "=== Nodes ==="
	kubectl get nodes
	@echo ""
	@echo "=== Namespaces ==="
	kubectl get namespaces

healthcheck:
	@bash scripts/healthcheck.sh
