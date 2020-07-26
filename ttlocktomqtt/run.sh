#!/usr/bin/env bashio

TTLOCK_CLIENT_APP=$(bashio::config 'ttlockclientapp')
TTLOCK_TOKEN=$(bashio::config 'ttlocktoken')
MQTT_BROKER_HOST=$(bashio::config 'mqttbrokerhost')
MQTT_BROKER_PORT=$(bashio::config 'mqttbrokerport')
MQTT_BROKER_USER=$(bashio::config 'mqttbrokeruser')
MQTT_BROKER_PASS=$(bashio::config 'mqttbrokerpass')

exec python3 /ttlock_adapter.py --client=${TTLOCK_CLIENT_APP} --token=${TTLOCK_TOKEN} --broker=${MQTT_BROKER_HOST} --port=${MQTT_BROKER_PORT} --user=${MQTT_BROKER_USER} --Pass=${MQTT_BROKER_PASS}