# TTLock2MQTT Add-on

Integrating your TTLock devices with Home Assistant over MQTT

## Installation

You need a MQTT Broker to use these Add-on. If you don't have one, install this Add-on:
https://github.com/home-assistant/hassio-addons/tree/master/mosquitto

1. Follow the instructions on [README](https://github.com/tonyldo/tonyldo-hassio-addons/blob/master/README.md) of this repo to add it in Supervisor Add-on Store.
1. Search for the "TTLock2MQTT" add-on at the Supervisor Add-on store.
1. Install the "TTLock2MQTT" add-on.
1. Configure the "TTLock2MQTT" add-on.
1. Start the "TTLock2MQTT" add-on.

## Configuration

**Note**: _Remember to restart the add-on when the configuration is changed._

Example add-on configuration:

```yaml
ttlockclientid: YOUR_TTLOCK_CLOUD_API_CLIENT_ID
ttlocktoken: YOUR_TTLOCK_CLOUD_API_TOKEN
publishbatterydelay: 300
publishstatedelay: 60
loglevel: INFO
maxthreads: 200
```
### Options: `ttlockclientid` and `ttlocktoken`

Follow this intructions to get your `YOUR_TTLOCK_CLOUD_API_CLIENT_ID` and `YOUR_TTLOCK_CLOUD_API_TOKEN`
https://github.com/tonyldo/ttlockio

### Option: `loglevel`

- `DEBUG`: Shows detailed debug information.
- `INFO`: Default informations.
- `WARNING`: Little alerts.
- `ERROR`:  Only errors.

### Option: `publishstatedelay` and `publishbatterydelay`

Time between two information publish in seconds.

### Option: `maxthreads`

Max number of threads for execution and the default number is 200. If you have more than 200 locks and gateway try two increase this number.
