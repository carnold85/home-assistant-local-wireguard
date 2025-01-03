# Local-WireGuard: A Custom Home Assistant Component

`local-wireguard` is a custom integration for Home Assistant that monitors WireGuard VPN peers by creating individual entities for each peer. This integration uses the local WireGuard tools (`wg`) to gather peer information and relies on the `wg show dump` command for a specified interface.

## Features

The `local-wireguard` component provides detailed information for each WireGuard peer, including:

- **State**: Whether the peer is active or inactive.
- **Endpoint**: The remote endpoint of the peer.
- **Allowed IPs**: The allowed IP addresses for the peer.
- **Last Handshake**: Timestamp of the last handshake with the peer.
- **Time Since Handshake**: Time elapsed since the last handshake.
- **RX/TX**: Data received and transmitted with the peer.
- **Keepalive**: Status of keepalive messages.
- **Status**: Overall status of the peer.
- **Public Key**: The public key of the peer.
- **PSK**: Always hidden for security.

## Prerequisites

1. **WireGuard** must be installed on the host system.
2. The `wg` command must be accessible and executable by Home Assistant. Special permissions are required to enable this functionality.

### Granting Permissions for Home Assistant

When using Home Assistant via `systemd`, add the following configuration to grant the required capabilities:

```bash
sudo systemctl edit home-assistant.service
```

Add the following lines:

```ini
[Service]
AmbientCapabilities=CAP_NET_ADMIN
CapabilityBoundingSet=CAP_NET_ADMIN
```

Restart Home Assistant after saving the changes:

```bash
sudo systemctl restart home-assistant.service
```

## Installation

1. Copy the `local-wireguard` integration to your Home Assistant custom components directory:
   ```
   custom_components/local_wireguard/
   ```

2. Ensure the `wg` command is installed and functioning on your system.

## Configuration

Enable the `local-wireguard` component by adding the configuration under `sensor` in your `configuration.yaml` file.

### Example Configuration

```yaml
sensor:
  - platform: local_wireguard
    interface: "wireguard0"  # Optional, default is "wg0"
    peers:
      # Assign friendly names to peers
      - pubkey: "aGVsbG8="
        name: "Roadwarrior-Smartphone"
      - pubkey: "bHV0bw=="
        name: "Remote-Laptop"
```

### Default Values

- **WG Path**: `/usr/bin/wg`
- **Interface**: `wg0`

If you use different paths or interfaces, specify them in the configuration.

## Example Sensor Attributes

Each WireGuard peer entity provides the following attributes:

- `Endpoint`: The endpoint of the peer.
- `Allowed IPs`: The allowed IP addresses for the peer.
- `Last Handshake`: Timestamp of the last handshake.
- `Time Since Handshake`: Time elapsed since the last handshake.
- `RX`: Data received from the peer.
- `TX`: Data transmitted to the peer.
- `Keepalive`: Keepalive status.
- `Status`: Peer status (active/inactive).
- `Public Key`: The peer's public key.
- `PSK`: Hidden for security.

## Troubleshooting

- Ensure Home Assistant has the necessary permissions to execute `wg`.
- Verify the `wg` command is installed and functioning on the system.
- Check the Home Assistant logs for error messages related to the `local-wireguard` integration.