#!/usr/bin/env bash
set -euo pipefail

export $(grep -v '^#' .env | xargs)
: "${ANTHROPIC_API_KEY:?Need to export ANTHROPIC_API_KEY or add to .env file}"


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

# LED Daemon
docker build -t chaos-led:0.1 "$BASE_DIR/services/led-daemon"
kind load docker-image chaos-led:0.1 --name $CLUSTER
kubectl apply -f "$BASE_DIR/k8s/led-daemon.yaml"

# Nyarlathotep LLM messenger
docker build -t nyarlathotep:0.1 "$BASE_DIR/services/nyarlathotep"
kind load docker-image nyarlathotep:0.1 --name $CLUSTER
kubectl create secret generic anthropic-api-key \
  --namespace shrine \
  --from-literal=api-key="$ANTHROPIC_API_KEY"

kubectl apply -f "$BASE_DIR/k8s/nyarlathotep-deploy.yaml"
kubectl apply -f "$BASE_DIR/k8s/nyarlathotep-svc.yaml"
