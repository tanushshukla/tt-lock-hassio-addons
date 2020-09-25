#!/usr/bin/env bashio

TTLOCK_CLIENT_APP=$(bashio::config 'ttlockclientapp')
TTLOCK_TOKEN=$(bashio::config 'ttlocktoken')
MQTT_BROKER_HOST=$(bashio::services mqtt "host")
MQTT_BROKER_PORT=$(bashio::services mqtt "port")
MQTT_BROKER_USER=$(bashio::services mqtt "username")
MQTT_BROKER_PASS=$(bashio::services mqtt "password")
PUBLISH_STATE_DELAY=$(bashio::config 'publishstatedelay')
PUBLISH_BATTERY_DELAY=$(bashio::config 'publishbatterydelay')
LOG_LEVEL=$(bashio::config 'loglevel')

exec python3 /ttlock_adapter.py --client=${TTLOCK_CLIENT_APP} --token=${TTLOCK_TOKEN} --broker=${MQTT_BROKER_HOST} --port=${MQTT_BROKER_PORT} --user=${MQTT_BROKER_USER} --Pass=${MQTT_BROKER_PASS} --State_delay=${PUBLISH_STATE_DELAY} --Battery_delay=${PUBLISH_BATTERY_DELAY} --log_level=${LOG_LEVEL}