#!/usr/bin/env bash
set -euo pipefail
CLUSTER=chaos-shrine
BASE_DIR=$PWD


kind delete cluster --name $CLUSTER || true

kind create cluster --config "$BASE_DIR/k8s/kind-config.yaml" --wait 360s

# Minimal Ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.2/deploy/static/provider/kind/deploy.yaml

# Namespaces
kubectl create ns system || true
kubectl create ns shrine || true
kubectl create ns valve  || true

docker build -t chaos-led:0.1 "$BASE_DIR/led-daemon"
kind load docker-image chaos-led:0.1 --name chaos-shrine
kubectl apply -f "$BASE_DIR/k8s/led-daemon.yaml"



