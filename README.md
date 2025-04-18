## Setup

### Build images
```shell
docker build -t sshpod:latest sshpod/
```

```shell
docker build -t webapp:latest webapp/
```

### Apply manifests
```shell
kubectl apply -f manifests/
```

### Verify deployment
```shell
kubectl get pods --all-namespaces
```

```shell
kubectl get services --all-namespaces
```

## Exploitation

### DockerDesktop
```
http://localhost:30001
```