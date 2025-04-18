#!/bin/bash
# probe.sh - Kubernetes Security Probe Script
# Collects info about namespaces, pods, services, configmaps, secrets, network policies, and RBAC objects.
# Highlights risky configurations and outputs a summary.

set -e

OUTPUT="probe_report_$(date +%Y%m%d_%H%M%S).txt"

function section() {
    echo -e "\n==================== $1 ====================\n" | tee -a "$OUTPUT"
}

function cmd() {
    echo ">$ $1" | tee -a "$OUTPUT"
    eval $1 | tee -a "$OUTPUT"
    echo | tee -a "$OUTPUT"
}

section "Namespaces"
cmd "kubectl get namespaces"

section "Pods (all namespaces)"
cmd "kubectl get pods -A -o wide"

section "Pods Running as Root (Security Risk)"
kubectl get pods -A -o json | jq -r '.items[] | select((.spec.containers[]?.securityContext?.runAsUser // .spec.securityContext?.runAsUser // 0) == 0) | "Namespace: \(.metadata.namespace), Pod: \(.metadata.name) runs as root!"' | tee -a "$OUTPUT"

section "Services (all namespaces)"
cmd "kubectl get svc -A -o wide"

section "External/Public Services"
kubectl get svc -A -o json | jq -r '.items[] | select(.spec.type == "LoadBalancer" or .spec.type == "NodePort") | "Namespace: \(.metadata.namespace), Service: \(.metadata.name), Type: \(.spec.type)"' | tee -a "$OUTPUT"

section "ConfigMaps (all namespaces)"
cmd "kubectl get configmaps -A"

section "Secrets (all namespaces)"
cmd "kubectl get secrets -A"

section "Network Policies (all namespaces)"
cmd "kubectl get networkpolicy -A"

section "Permissive Network Policies (allow all ingress)"
kubectl get networkpolicy -A -o json | jq -r '.items[] | select((.spec.ingress == null) or ((.spec.ingress | length) == 0)) | "Namespace: \(.metadata.namespace), NetworkPolicy: \(.metadata.name) allows all ingress!"' | tee -a "$OUTPUT"

section "RBAC Roles"
cmd "kubectl get roles,clusterroles -A"

section "RBAC RoleBindings"
cmd "kubectl get rolebindings,clusterrolebindings -A"

section "Summary"
echo "Probe complete. Full report saved to $OUTPUT." | tee -a "$OUTPUT"
