# Kubernetes deploy (local)
This directory contains basic manifests. For local `kind`:

1) Build images locally:
```bash
docker build -t orchestrator:local ./orchestrator
docker build -t sample-spring-service:local ./spring-service
```

2) Load images into kind:
```bash
kind load docker-image orchestrator:local
kind load docker-image sample-spring-service:local
```

3) Apply manifests:
```bash
kubectl apply -f k8s/
```

4) Port-forward:
```bash
kubectl -n ops-demo port-forward svc/orchestrator 8000:8000
kubectl -n ops-demo port-forward svc/sample-spring-service 8080:8080
```
