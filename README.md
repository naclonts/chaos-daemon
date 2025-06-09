# Chaos Daemon

A Kubernetes cluster of emergent behavior.

![ASCII-ish art of a sever-skull floating in a data center by chatgpt](./assets/servo_skull_in_a_datacenter.png)

### Run

Requires Kind.

```sh
./scripts/dev-cluster.sh
```

> Some behavior requires specific node hardware (e.g., the LED Daemon).

To chat with the Nyarlathotep language model pod:

```sh
./scripts/chat.py
```

### Behavior

- Erratic LED manipulation from Raspberry Pi 5 node
- Portal to eldritch language model that can control the LEDs via MCP calls
