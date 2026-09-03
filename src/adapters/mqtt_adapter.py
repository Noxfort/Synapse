# SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
# Copyright (C) 2026 Noxfort Systems
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# File: src/adapters/mqtt_adapter.py
# Author: Gabriel Moraes
# Date: 2026-08-29

import json
import threading
from typing import Any, Dict, List, Optional

from src.domain.entities import DataSource
from src.adapters.base_adapter import BaseIngestionAdapter


class MqttIngestionAdapter(BaseIngestionAdapter):
    """
    MQTT Ingestion Adapter (Pub-Sub / IoT Architecture).
    Subscribes to telemetry topics published by Edge AI cameras, sensors, and roadside units.
    Extracts sensor IDs from topic patterns (e.g., 'traffic/cameras/{sensor_id}/telemetry').
    """

    def __init__(
        self,
        adapter_id: str = "mqtt_broker_adapter",
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topics: Optional[List[str]] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
    ):
        super().__init__(adapter_id=adapter_id, transport_name="MQTT")
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topics = topics or ["synapse/+/telemetry", "traffic/cameras/#"]
        self.username = username
        self.password = password
        self.use_tls = use_tls

        self._client: Any = None
        self._mqtt_available = False

    def _do_start(self) -> None:
        """Initializes MQTT client if library is installed; otherwise logs gracefully."""
        try:
            import paho.mqtt.client as mqtt
            self._mqtt_available = True
            try:
                # paho-mqtt v2 CallbackAPIVersion support
                from paho.mqtt.enums import CallbackAPIVersion
                self._client = mqtt.Client(CallbackAPIVersion.VERSION1, client_id=f"synapse_{self._adapter_id}")
            except Exception:
                self._client = mqtt.Client(client_id=f"synapse_{self._adapter_id}")

            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)
            if self.use_tls:
                self._client.tls_set()

            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.connect_async(self.broker_host, self.broker_port, keepalive=60)
            self._client.loop_start()
            self._logger.info(f"📡 [MqttAdapter] Connected to MQTT broker at {self.broker_host}:{self.broker_port}")

        except ImportError:
            self._mqtt_available = False
            self._logger.info(
                f"ℹ️ [MqttAdapter] 'paho-mqtt' not installed in environment. "
                f"Operating in virtual/in-memory adapter mode for '{self._adapter_id}'."
            )
        except Exception as e:
            self._logger.warning(f"⚠️ [MqttAdapter] Failed to connect to MQTT broker ({self.broker_host}:{self.broker_port}): {e}")

    def _do_stop(self) -> None:
        if self._mqtt_available and self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                self._logger.debug(f"[MqttAdapter] Error disconnecting MQTT: {e}")
            self._client = None

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: int) -> None:
        if rc == 0:
            self._logger.info(f"✅ [MqttAdapter] Subscribing to topics: {self.topics}")
            for topic in self.topics:
                client.subscribe(topic)
        else:
            self._logger.error(f"❌ [MqttAdapter] Connection refused with code: {rc}")

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        """Decodes inbound MQTT message and forwards to pipeline."""
        try:
            topic = msg.topic
            raw_str = msg.payload.decode("utf-8", errors="ignore").strip()

            # Attempt JSON parse
            try:
                payload = json.loads(raw_str)
            except Exception:
                payload = {"value": raw_str}

            source_id = self._extract_source_id_from_topic(topic, payload)

            self.emit_packet(
                source_id=source_id,
                payload=payload,
                metadata={
                    "transport": "MQTT",
                    "topic": topic,
                    "qos": getattr(msg, "qos", 0),
                },
            )
        except Exception as e:
            self._logger.error(f"❌ [MqttAdapter] Error processing MQTT message: {e}", exc_info=True)

    def _extract_source_id_from_topic(self, topic: str, payload: Any) -> str:
        """Resolves source ID from payload body or topic tokens using heuristic filtering."""
        if isinstance(payload, dict):
            for key in ["source_id", "device_id", "sensor_id", "id"]:
                if key in payload and payload[key]:
                    return str(payload[key])

        ignore_tokens = {
            "traffic", "cameras", "camera", "sensors", "sensor",
            "devices", "device", "telemetry", "data", "events",
            "event", "feed", "stream", "synapse", "inbound", "push"
        }
        parts = [p for p in topic.strip("/").split("/") if p]
        
        for p in parts:
            if p.lower() not in ignore_tokens:
                return p

        return parts[-1] if parts else "mqtt_sensor"

    def simulate_message(self, topic: str, raw_payload: Any) -> None:
        """Helper for unit tests or simulated MQTT ingestions."""
        source_id = self._extract_source_id_from_topic(topic, raw_payload)
        self.emit_packet(
            source_id=source_id,
            payload=raw_payload,
            metadata={"transport": "MQTT", "topic": topic, "simulated": True},
        )
