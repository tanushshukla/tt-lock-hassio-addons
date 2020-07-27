import paho.mqtt.client as mqtt
import time
import threading
import concurrent.futures
import getopt
import sys
import logging
from ttlockwrapper import TTLock, TTlockAPIError, constants


class TTLockToMqttClient(mqtt.Client):
    def __init__(self, id, ttlock, broker, port, broker_user, broker_pass, keepalive):
        mqttClientId = "lOCK-{}-{}".format(str(id), str(int(time.time())))
        super().__init__(mqttClientId, False)
        self.ttlock = ttlock
        self.mqttClientId = mqttClientId
        self.connected_flag = False
        self.on_connect = TTLockToMqttClient.cb_on_connect
        self.on_disconnect = TTLockToMqttClient.cb_on_disconnect
        self.on_message = TTLockToMqttClient.cb_on_message
        self.lastPublishInfo = time.time()
        self.broker_host = broker
        self.broker_port = port
        self.keepalive_mqtt = keepalive
        if broker_user and broker_pass:
            self.username_pw_set(broker_user, password=broker_pass)

    def sendMensage(self, topic, msg, retain=False):
        logging.debug('Client {} sending mensage "{}" to topic "{}" and retained {}'.format(
            self.mqttClientId, msg, topic, retain))
        self.publish(topic, msg, 0, retain)

    def mqttConnection(self):
        logging.debug("Try connection for TTlock Mqtt Client {} at {}:{}".format(
            self.mqttClientId, self.broker_host, self.broker_port))
        self.connect(self.broker_host, self.broker_port, self.keepalive_mqtt)

    @classmethod
    def cb_on_message(cls, client, userdata, message):
        try:
            time.sleep(1)
            logging.debug("Client {} message received: {}".format(client.mqttClientId, str(message.payload.decode("utf-8"))))
            client.handleMessage(message)
        except Exception:
            logging.exception('While on received mqtt message for lock {}:'.format(client.getLockId()))

    @classmethod
    def cb_on_disconnect(cls, client, userdata, rc):
        client.connected_flag = False  # set flag
        logging.info("Client {} disconnected!".format(client.mqttClientId))

    @classmethod
    def cb_on_connect(cls, client, userdata, flags, rc):
        try:
            if rc == 0:
                client.connected_flag = True  # set flag
                logging.info("Client {} connected OK!".format(client.mqttClientId))
                if client.COMMAND_TOPIC:
                    logging.info("Client {} subscribe on command topic: {}".format(
                        client.mqttClientId, client.COMMAND_TOPIC))
                    client.subscribe(client.COMMAND_TOPIC)
                client.sendDiscoveryMsgs()
                client.forcePublishInfos()
            else:
                logging.error("Client {} Bad connection Returned code= {}".format(
                    client.mqttClientId, rc))
        except Exception:
            logging.exception('While on connect mqtt for lock {}:'.format(client.getLockId()))


class TTLockToMqttClientLock(TTLockToMqttClient):

    def __init__(self, lock, gateway, ttlock, broker, port, broker_user, broker_pass, keepalive):
        self.lock = lock
        self.gateway = gateway
        self.DISCOVERY_LOCK_TOPIC = 'homeassistant/lock/ttlock/{}_lock/config'.format(
            self.getLockId())
        self.DISCOVERY_SENSOR_TOPIC = 'homeassistant/sensor/ttlock/{}_battery/config'.format(
            self.getLockId())
        self.DISCOVERY_BINARY_SENSOR_TOPIC = 'homeassistant/binary_sensor/ttlock/{}_state/config'.format(
            self.getLockId())
        self.BATTERY_LEVEL_SENSOR_TOPIC = 'ttlocktomqtt/{}/battery'.format(
            self.getLockId())
        self.COMMAND_TOPIC = 'ttlocktomqtt/{}/command'.format(self.getLockId())
        self.STATE_SENSOR_TOPIC = 'ttlocktomqtt/{}/state'.format(
            self.getLockId())
        self.DISCOVERY_STATE_SENSOR_PAYLOAD = '{{"device_class": "lock", "name": "{} state", "state_topic": "{}", "value_template": "{{{{ value_json.state }}}}", "uniq_id":"{}_state","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}} }}'
        self.DISCOVERY_LOCK_PAYLOAD = '{{"name": "{} lock", "command_topic": "{}", "state_topic": "{}", "value_template": "{{{{ value_json.state }}}}", "uniq_id":"{}_lock","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}} }}'
        self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD = '{{"device_class": "battery", "name": "{} battery", "state_topic": "{}", "unit_of_measurement": "%", "value_template": "{{{{ value_json.battery }}}}", "uniq_id":"{}_battery","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}} }}'
        self.STATE_PAYLOAD = '{{"state": "{}"}}'
        self.BATTERY_LEVEL_PAYLOAD = '{{"battery": {}}}'

        super().__init__(self.getLockId(), ttlock, broker,
                         port, broker_user, broker_pass, keepalive)

    def getName(self):
        return self.lock.get(constants.LOCK_ALIAS_FIELD)

    def getLockId(self):
        return self.lock.get(constants.LOCK_ID_FIELD)

    def getMac(self):
        return self.lock.get(constants.LOCK_MAC_FIELD)

    def getGatewayId(self):
        return self.gateway.get(constants.GATEWAY_ID_FIELD)

    def handleMessage(self, message):
        result = False
        command = str(message.payload.decode("utf-8"))
        if command == 'LOCK':
            result = self.ttlock.lock(self.getLockId())
        elif command == 'UNLOCK':
            result = self.ttlock.unlock(self.getLockId())
        else:
            logging.info('Invalid command.')
            return
        if not result:
            logging.warning(
                'Fail send to TTLOCK API command to lock {}.'.format(self.getLockId()))
            # todo: send unavailble msg
            return
        self.forcePublishInfos()

    def publishInfos(self):
        #logging.info("Time elapsed since last info send for {} lock: {}".format(self.getLockId(), time.time()-self.lastPublishInfo))
        if time.time()-self.lastPublishInfo > DELAY_BETWEEN_LOCK_PUBLISH_INFOS:
            self.forcePublishInfos()

    def forcePublishInfos(self):
        try:
            logging.info(
                'Publish mqtt lock {} information.'.format(self.getLockId()))
            self.sendLockState()
            self.sendLockBatteryLevel()
        except Exception as error:
            logging.error('While publish mqtt lock {} information: {}'.format(
                self.getLockId(), str(error)))
        self.lastPublishInfo = time.time()

    def sendLockBatteryLevel(self):
        batteryLevel = self.ttlock.lock_electric_quantity(self.getLockId())
        msg = self.BATTERY_LEVEL_PAYLOAD.format(batteryLevel)
        self.sendMensage(self.BATTERY_LEVEL_SENSOR_TOPIC, msg)

    def sendLockState(self):
        # Open state of lock:0-locked,1-unlocked,2-unknown
        state = self.ttlock.lock_state(self.getLockId())
        if state == 2:
            logging.warning(
                'While send {} lock state TTlockAPI return "unknown".'.format(self.getLockId()))
            return
        lock_is = 'UNLOCKED' if state else 'LOCKED'
        msg = self.STATE_PAYLOAD.format(lock_is)
        self.sendMensage(self.STATE_SENSOR_TOPIC, msg)

    def sendDiscoveryMsgs(self):
        logging.info(
            'Sending discoveries msgs for client {}.'.format(self.mqttClientId))
        msg = self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD.format(self.getName(
        ), self.BATTERY_LEVEL_SENSOR_TOPIC, self.getLockId(), self.getLockId(), self.getMac(), self.getGatewayId())
        self.sendMensage(self.DISCOVERY_SENSOR_TOPIC, msg, True)
        """msg = self.DISCOVERY_STATE_SENSOR_PAYLOAD.format(self.getName(
        ), self.STATE_SENSOR_TOPIC, self.getLockId(), self.getLockId(), self.getMac(), self.getGatewayId())
        self.sendMensage(self.DISCOVERY_BINARY_SENSOR_TOPIC, msg, True)"""
        msg = self.DISCOVERY_LOCK_PAYLOAD.format(self.getName(), self.COMMAND_TOPIC, self.STATE_SENSOR_TOPIC, self.getLockId(
        ), self.getLockId(), self.getMac(), self.getGatewayId())
        self.sendMensage(self.DISCOVERY_LOCK_TOPIC, msg, True)


def client_loop(lock, gateway, ttlock, broker, port, broker_user, broker_pass, keepalive, loop_delay=2.0, run_forever=False):
    ttlockToMqttClient = None
    try:
        ttlockToMqttClient = TTLockToMqttClientLock(
            lock, gateway, ttlock, broker, port, broker_user, broker_pass, keepalive)
        logging.info("Created TTlock Mqtt Client for lockid: {}".format(
            ttlockToMqttClient.mqttClientId))
        bad_connection = 0
        ttlockToMqttClient.mqttConnection()
        while run_flag:  # loop
            ttlockToMqttClient.loop(loop_delay)
            if ttlockToMqttClient.connected_flag:
                ttlockToMqttClient.publishInfos()
            else:
                if bad_connection > 5 and not run_forever:
                    logging.error("5 times bad connection for: {}".format(
                        lock.get(constants.LOCK_ID_FIELD)))
                    break
                bad_connection += 1
                time.sleep(10)

        if ttlockToMqttClient.connected_flag:
            ttlockToMqttClient.disconnect()

    except Exception as e:
        logging.exception("Client Loop Thread Error {}".format(
            ttlockToMqttClient.mqttClientId))

    finally:
        logging.debug("Return future for lockid: {}".format(
            ttlockToMqttClient.mqttClientId))
        return ttlockToMqttClient


def createClients(broker, port, broker_user, broker_pass, ttlock_client, ttlock_token):
    ttlock = TTLock(ttlock_client, ttlock_token)
    for gateway in ttlock.get_gateway_generator():
        for lock in ttlock.get_locks_per_gateway_generator(gateway.get(constants.GATEWAY_ID_FIELD)):
            if lock.get(constants.LOCK_ID_FIELD) in client_futures.keys() and not client_futures.get(lock.get(constants.LOCK_ID_FIELD)).done():
                logging.info('Lock {} mqtt client already created...'.format(
                    lock.get(constants.LOCK_ID_FIELD)))

            else:
                client_futures[lock.get(constants.LOCK_ID_FIELD)] = executor.submit(
                    client_loop, lock, gateway, ttlock, broker, port, broker_user, broker_pass, DELAY_BETWEEN_LOCK_PUBLISH_INFOS*2)
            time.sleep(DELAY_BETWEEN_NEW_THREADS_CREATION)
        time.sleep(DELAY_BETWEEN_NEW_THREADS_CREATION)


def main(broker, port, broker_user, broker_pass, ttlock_client, ttlock_token):
    try:
        if not ttlock_client or not ttlock_token:
            raise ValueError('Invalid ttlock client or token.')

        logging.debug("Starting main loop...")
        while True:
            try:
                createClients(broker, port, broker_user, broker_pass,
                              ttlock_client, ttlock_token)
                logging.info("Current threads: {}".format(
                    threading.active_count()))
            except Exception as e:
                logging.exception("Error main method")
            time.sleep(DELAY_BETWEEN_NEW_THREADS_CREATION)

    except KeyboardInterrupt:
        logging.info("Ending...")
        global run_flag
        run_flag = False
        for lockId, future in client_futures.items():
            logging.info("{} thread is over!".format(
                future.result().getLockId()))
    except ValueError as e:
        logging.exception('Exiting script...')


def isEmptyStr(s):
    return s == 'null' or len(s) == 0 or s.isspace()


DELAY_BETWEEN_NEW_THREADS_CREATION = 60
DELAY_BETWEEN_LOCK_PUBLISH_INFOS = 60
run_flag = True
client_futures = dict()
executor = concurrent.futures.ThreadPoolExecutor()

if __name__ == '__main__':
    broker = 'localhost'
    port = 1883
    broker_user = None
    broker_pass = None
    ttlock_client = None
    ttlock_token = None
    loglevel = 'INFO'
    full_cmd_arguments = sys.argv
    argument_list = full_cmd_arguments[1:]
    short_options = 'b:p:u:P:c:t:l:'
    long_options = ['broker=', 'port=', 'user=',
                    'Pass=', 'client=', 'token=', 'log_level=']
    try:
        arguments, values = getopt.getopt(
            argument_list, short_options, long_options)
    except getopt.error as e:
        raise ValueError('Invalid parameters!')

    for current_argument, current_value in arguments:
        if isEmptyStr(current_value):
            break
        elif current_argument in ("-b", "--broker"):
            broker = current_value
        elif current_argument in ("-p", "--port"):
            port = current_value
        elif current_argument in ("-u", "--user"):
            broker_user = current_value
        elif current_argument in ("-P", "--Pass"):
            broker_pass = current_value
        elif current_argument in ("-c", "--client"):
            ttlock_client = current_value
        elif current_argument in ("-t", "--token"):
            ttlock_token = current_value
        elif current_argument in ("-l", "--log_level"):
            loglevel = current_value

    numeric_level = getattr(logging, loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)

    logging.basicConfig(level=numeric_level, datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)-15s - [%(levelname)s] %(module)s: %(message)s', )

    logging.debug("Options: {}, {}, {}, {}, {}, {}".format(
        ttlock_client, ttlock_token, broker, port, broker_user, broker_pass))
    main(broker, port, broker_user, broker_pass, ttlock_client, ttlock_token)
