import logging
import subprocess
from datetime import datetime, timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(seconds=30)

existing_entities = {}
pubkey_to_name_map = {}

DEFAULT_WG_PATH = "/usr/bin/wg"
DEFAULT_INTERFACE = "wg0"


class WireGuardPeerSensor(Entity):

    def __init__(self, coordinator, peer_key, initial_data, friendly_name=None):
        self.coordinator = coordinator
        self._peer_key = peer_key
        self._attributes = initial_data
        self._friendly_name = friendly_name

    @property
    def unique_id(self):
        return self._peer_key

    @property
    def name(self):
        return f"WireGuard Peer {self._friendly_name if self._friendly_name else self._peer_key}"

    @property
    def state(self):
        # State active inactive for sensor
        return (
            "Active" if self._attributes.get("status", "") == "Active" else "Inactive"
        )

    @property
    def extra_state_attributes(self):
        return {
            "Endpoint": self._attributes.get("endpoint"),
            "Allowed IPs": self._attributes.get("allowed_ips"),
            "Last Handshake": self._attributes.get("latest_handshake"),
            "Time Since Handshake": self._attributes.get("time_since_handshake"),
            "RX": self._attributes.get("rx"),
            "TX": self._attributes.get("tx"),
            "Keepalive": self._attributes.get("keepalive"),
            "Status": self._attributes.get("status"),
            "Public Key": self._attributes.get("public_key"),
            "PSK": "(hidden)",  # self._attributes.get("psk"),
        }

    @property
    def should_poll(self):
        # Should not be polled, we have a coordinator instead
        return False

    async def async_added_to_hass(self):
        # Add an listener for the coordinator for the update
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_on_coordinator_update)
        )

    def async_on_coordinator_update(self):
        # Update was triggered so update data and also wirte update to HA
        self.update_data()
        self.async_write_ha_state()

    def update_data(self):
        self._attributes = self.coordinator.data.get(self._peer_key, {})
        self._friendly_name = pubkey_to_name_map.get(self._peer_key, self._peer_key)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # I dont know why this function is called twice if i use sesor - platform configuuration. But with this hack it works just calling once
    if "platform" not in config:
        return

    global pubkey_to_name_map
    # Get the Alias configuration from configuration.yaml
    wireguard_peers_config = config.get("peers", [])
    # Create a dictionary to map public keys to friendly names
    pubkey_to_name_map = (
        {peer["pubkey"]: peer.get("name") for peer in wireguard_peers_config}
        if wireguard_peers_config
        else {}
    )

    # Get iw_path and interface from configuration, or use defaults
    wg_path = config.get("iw_path", DEFAULT_WG_PATH)
    interface = config.get("interface", DEFAULT_INTERFACE)

    # Fetcher Function
    async def fetch_wireguard_data():
        data = {}
        try:
            output = subprocess.check_output(
                [wg_path, "show", interface, "dump"], text=True
            ).splitlines()
            now = datetime.now().timestamp()

            for line in output[1:]:
                fields = line.split()
                # 0 => Public Key
                # 1 => PSK
                # 2 => Endpoint
                # 3 => Allowed IPs
                # 4 => Latest Handshake
                # 5 => Transfered Bytess
                # 6 => Recieved Bytes
                # 7 => Keepalive
                latest_handshake = int(fields[4])
                time_since_handshake = (
                    int(now - latest_handshake) if latest_handshake > 0 else None
                )
                status = (
                    "Active"
                    if latest_handshake > 0 and time_since_handshake < 120
                    else "Inactive"
                )
                data[fields[0]] = {
                    "endpoint": fields[2],
                    "allowed_ips": fields[3],
                    "public_key": fields[0],
                    "psk": fields[1],
                    "latest_handshake": latest_handshake,
                    "time_since_handshake": time_since_handshake,
                    "status": status,
                    "rx": int(fields[5]),
                    "tx": int(fields[6]),
                    "keepalive": fields[7],
                }
        except Exception as e:
            _LOGGER.error(f"Error fetching WireGuard data: {e}")
        return data

    # The coordinator for all entities. So only on data fetch used to update all entities
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="wireguard_peers",
        update_method=fetch_wireguard_data,
        update_interval=UPDATE_INTERVAL,
    )

    # Manual trigger
    await coordinator.async_refresh()

    # First inital add - later the update will do the rest
    global existing_entities
    entities = []
    for peer_key, peer_data in coordinator.data.items():
        # Get the friendly name if provided else None
        friendly_name = pubkey_to_name_map.get(peer_key)
        new_entity = WireGuardPeerSensor(
            coordinator, peer_key, peer_data, friendly_name
        )
        existing_entities[peer_key] = new_entity
        entities.append(new_entity)
    async_add_entities(entities, True)

    # Handle dynamic additions and removals
    def coordinator_update():
        global existing_entities
        global pubkey_to_name_map

        new_entities = []
        for peer_key, peer_data in coordinator.data.items():
            if peer_key not in existing_entities:
                # Get the friendly name if provided else None
                friendly_name = pubkey_to_name_map.get(peer_key)
                # Add new entity
                new_entity = WireGuardPeerSensor(
                    coordinator, peer_key, peer_data, friendly_name
                )
                existing_entities[peer_key] = new_entity
                new_entities.append(new_entity)
                _LOGGER.info(f"WireGuard peer {peer_key} added")

        # Add new entities to Home Assistant
        if new_entities:
            async_add_entities(new_entities, True)

        # Remove (delete complete) not used peers
        for peer_key in list(existing_entities.keys()):
            if peer_key not in coordinator.data:
                entity = existing_entities.pop(peer_key)
                hass.add_job(entity.async_remove())
                _LOGGER.info(f"WireGuard peer {peer_key} deleted")

    # Link the coordinator update method
    coordinator.async_add_listener(coordinator_update)
