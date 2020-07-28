# TTLockToMQTT Add-on

Integrating your TTLock devices with Home Assistant over MQTT

## Installation

1. Follow the instructions on [README](./README.md) of this repo to add it in Supervisor Add-on Store.
1. Search for the "TTLock2MQTT" add-on at the Supervisor Add-on store.
1. Install the "TTLock2MQTT" add-on.
1. Configure the "TTLock2MQTT" add-on.
1. Start the "TTLock2MQTT" add-on.

## Configuration

**Note**: _Remember to restart the add-on when the configuration is changed._

Example add-on configuration:

```yaml
ttlockclientapp: YOUR_TTLOCK_CLOUD_API_CLIENT_APP
ttlocktoken: YOUR_TTLOCK_CLOUD_API_TOKEN
mqttbrokerhost: 192.0.0.7
mqttbrokerport: '1883'
mqttbrokeruser: BROKER_USER
mqttbrokerpass: BROKER_PASS
loglevel: info
```
### Options: `ttlockclientapp` and `ttlocktoken`

Follow this intructions to get your `YOUR_TTLOCK_CLOUD_API_CLIENT_APP` and `YOUR_TTLOCK_CLOUD_API_TOKEN`
https://github.com/tonyldo/ttlockio

### Options: `mqttbrokerhost`, `mqttbrokerport`, `mqttbrokeruser` and `mqttbrokerpass`

Your MQTT Broker address and credentials. If you don't know what this is, install this addon:
https://github.com/home-assistant/hassio-addons/tree/master/mosquitto

### Option: `loglevel`

- `debug`: Shows detailed debug information.
- `info`: Default informations.
- `warning`: Little alerts.
- `error`:  Only errors.
