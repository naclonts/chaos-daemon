#!/usr/bin/env bash
set -euo pipefail
CLUSTER=chaos-shrine
MYDIR="$(dirname "$(readlink -f "$0")")"

# kind delete-cluster --name $CLUSTER || true

kind create cluster --config "$MYDIR/kind-config.yaml" --wait 360s

# Minimal Ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.2/deploy/static/provider/kind/deploy.yaml

# Namespaces
kubectl create ns system || true
kubectl create ns shrine || true
kubectl create ns valve  || true

