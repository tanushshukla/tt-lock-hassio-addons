# TTLockToMQTT Add-on

Integrating yours ttlocks devices on your home assistan instance over MQTT.

## Installation

1. Follow the instructions on README of this repo to add it in Supervisor Add-on Store.
1. Search for the "TTLock" add-on at the Supervisor Add-on store.
1. Install the "TTLock" add-on.
1. Configure the "TTLock" add-on.
1. Start the "TTLock" add-on.

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
loglevel: INFO
```
### Options: `ttlockclientapp` and `ttlocktoken`

Follow this intructions to get yours YOUR_TTLOCK_CLOUD_API_CLIENT_APP and YOUR_TTLOCK_CLOUD_API_TOKEN
https://github.com/tonyldo/ttlockio

### Options: `mqttbrokerhost`, `mqttbrokerport`, `mqttbrokeruser` and `mqttbrokerpass`

Yours MQTT address and credentials. If you are doesn't know what is this, go to this addon:
https://github.com/home-assistant/hassio-addons/tree/master/mosquitto

### Option: `loglevel`

- `debug`: Shows detailed debug information.
- `info`: Default informations.
- `warning`: Little alerts.
- `error`:  Only errors.