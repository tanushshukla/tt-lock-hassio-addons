import paho.mqtt.client as mqtt
import time
import threading
import concurrent.futures
import getopt
import sys
from ttlockwrapper import TTLock,TTlockAPIError, constants

DELAY_BETWEEN_NEW_THREADS_CREATION = 60
DELAY_BETWEEN_LOCK_PUBLISH_INFOS = 60


class TTLockToMqttClient(mqtt.Client):
    def __init__(self, id, ttlock, broker, port, broker_user, broker_pass,keepalive):
        mqttClientId = "lOCK-{}-{}".format(str(id), str(int(time.time())))
        super().__init__(mqttClientId)
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

    def sendMensage(self, topic, msg):
        print('Client {} sending mensage "{}" to topic "{}"'.format(
            self.mqttClientId, msg, topic))
        self.publish(topic, msg)
        
    def mqttConnection(self):
        self.connect(self.broker_host, self.broker_port, self.keepalive_mqtt)

    @classmethod
    def cb_on_message(cls, client, userdata, message):
        time.sleep(1)
        print("Client {} message received: {}".format(
            client.mqttClientId, str(message.payload.decode("utf-8"))))
        client.handleMessage(message)

    @classmethod
    def cb_on_disconnect(cls, client, userdata, rc):
        client.connected_flag = False  # set flag
        print("Client {} disconnected!".format(client.mqttClientId))

    @classmethod
    def cb_on_connect(cls, client, userdata, flags, rc):
        if rc == 0:
            client.connected_flag = True  # set flag
            print("Client {} connected OK!".format(client.mqttClientId))
            if client.COMMAND_TOPIC:
                print("Client {} subscribe on command topic: {}".format(client.mqttClientId,client.COMMAND_TOPIC))
                client.subscribe(client.COMMAND_TOPIC)
            client.sendDiscoveryMsgs()
        else:
            print("Client {} Bad connection Returned code= {}".format(
                client.mqttClientId, rc))


class TTLockToMqttClientLock(TTLockToMqttClient):

    def __init__(self, lock, gateway, ttlock, broker, port, broker_user, broker_pass,keepalive):
        self.lock = lock
        self.gateway = gateway
        self.DISCOVERY_LOCK_TOPIC = 'test/lock/ttlock/{}_lock/config'.format(
            self.getLockId())
        self.DISCOVERY_SENSOR_TOPIC = 'test/sensor/ttlock/{}_battery/config'.format(
            self.getLockId())
        self.DISCOVERY_BINARY_SENSOR_TOPIC = 'test/binary_sensor/ttlock/{}_state/config'.format(
            self.getLockId())
        self.BATTERY_LEVEL_SENSOR_TOPIC = 'ttlocktomqtt/{}/battery'.format(
            self.getLockId())
        self.COMMAND_TOPIC = 'ttlocktomqtt/{}/command'.format(self.getLockId())
        self.STATE_SENSOR_TOPIC = 'ttlocktomqtt/{}/state'.format(
            self.getLockId())
        self.DISCOVERY_STATE_SENSOR_PAYLOAD = '{{"device_class": "lock", "name": "{}", "state_topic": "{}", "value_template": "{{ value_json.lock}}", "uniq_id":"{}_state","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}}, "via_device":"{}" }}'
        self.DISCOVERY_LOCK_PAYLOAD = '{{"name": "{}", "command_topic": "{}", "state_topic": "{}", "value_template": "{{ value_json.command}}", "uniq_id":"{}_lock","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}}, "via_device":"{}" }}'
        self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD = '{{"device_class": "battery", "name": "{}", "state_topic": "{}", "unit_of_measurement": "%", "value_template": "{{ value_json.battery}}", "uniq_id":"{}_battery","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}}, "via_device":"{}" }}'
        self.STATE_PAYLOAD = '{{"lock": "{}"}}'
        self.BATTERY_LEVEL_PAYLOAD = '{{"battery": {}}}'

        super().__init__(self.getLockId(), ttlock, broker, port, broker_user, broker_pass,keepalive)

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
        if command == 'lock':
            result = self.ttlock.lock(self.getLockId())
        elif command == 'unlock':
            result = self.ttlock.unlock(self.getLockId())
        else:
            print('Invalid command.')
            return
        if not result:
            # todo: send unavailble msg
            return
        self.publishInfos()

    def publishInfos(self):
        #print("Time elapsed since last info send for {} lock: {}".format(self.getLockId(), time.time()-self.lastPublishInfo))
        if time.time()-self.lastPublishInfo > DELAY_BETWEEN_LOCK_PUBLISH_INFOS*3:
            self.forcePublishInfos()

    def forcePublishInfos(self):
        try:
            print('Publish mqtt lock {} information.'.format(self.getLockId()))
            self.sendLockState()
            self.sendLockBatteryLevel()
        except Exception as error:
            print('While publish mqtt lock {} information: {}'.format(self.getLockId(),error))
        self.lastPublishInfo = time.time()


    def sendLockBatteryLevel(self):
        batteryLevel = self.ttlock.lock_electric_quantity(self.getLockId())
        msg = self.BATTERY_LEVEL_PAYLOAD.format(batteryLevel)
        self.sendMensage(self.BATTERY_LEVEL_SENSOR_TOPIC, msg)

    def sendLockState(self):
        # Open state of lock:0-locked,1-unlocked,2-unknown
        state = self.ttlock.lock_state(self.getLockId())
        if state == 2:
            print('While send {} lock state TTlockAPI return "unknown".'.format(self.getLockId()))
            return
        lock_is = 'unlocked' if state else 'locked'
        msg = self.STATE_PAYLOAD.format(lock_is)
        self.sendMensage(self.STATE_SENSOR_TOPIC, msg)

    def sendDiscoveryMsgs(self):
        print('Sending discoveries msgs for client {}.'.format(self.mqttClientId))
        msg = self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD.format(self.getName(
        ), self.BATTERY_LEVEL_SENSOR_TOPIC, self.getLockId(), self.getLockId(), self.getMac(), self.getGatewayId())
        self.sendMensage(self.DISCOVERY_SENSOR_TOPIC, msg)
        msg = self.DISCOVERY_STATE_SENSOR_PAYLOAD.format(self.getName(
        ), self.STATE_SENSOR_TOPIC, self.getLockId(), self.getLockId(), self.getMac(), self.getGatewayId())
        self.sendMensage(self.DISCOVERY_BINARY_SENSOR_TOPIC, msg)
        msg = self.DISCOVERY_LOCK_PAYLOAD.format(self.getName(), self.COMMAND_TOPIC, self.STATE_SENSOR_TOPIC, self.getLockId(
        ), self.getLockId(), self.getMac(), self.getGatewayId())
        self.sendMensage(self.DISCOVERY_LOCK_TOPIC, msg)
    
def client_loop(lock, gateway, ttlock, broker, port, broker_user, broker_pass, keepalive, loop_delay=1.0, run_forever=False):
    ttlockToMqttClient = TTLockToMqttClientLock(lock, gateway, ttlock, broker, port, broker_user, broker_pass,keepalive)
    print("Created TTlock Mqtt Client for lockid: {}".format(
        ttlockToMqttClient.mqttClientId))
    bad_connection = 0
    ttlockToMqttClient.mqttConnection()
    while run_flag:  # loop
        ttlockToMqttClient.loop(loop_delay)
        if ttlockToMqttClient.connected_flag:
            ttlockToMqttClient.publishInfos()
        else:
            if bad_connection > 5 and not run_forever:
                break
            bad_connection += 1
            time.sleep(10)

    if ttlockToMqttClient.connected_flag:
        ttlockToMqttClient.disconnect()

    return ttlockToMqttClient


def createClients(broker, port, broker_user, broker_pass, ttlock_client, ttlock_token):
    ttlock = TTLock(ttlock_client, ttlock_token)
    for gateway in ttlock.get_gateway_generator():
        for lock in ttlock.get_locks_per_gateway_generator(gateway.get(constants.GATEWAY_ID_FIELD)):
            if lock.get(constants.LOCK_ID_FIELD) in client_futures.keys() and not client_futures.get(lock.get(constants.LOCK_ID_FIELD)).done():
                print('Lock {} mqtt client already created...'.format(lock.get(constants.LOCK_ID_FIELD)))
                
            else:
                client_futures[lock.get(constants.LOCK_ID_FIELD)] = executor.submit(client_loop, lock, gateway, ttlock, broker, port, broker_user, broker_pass, DELAY_BETWEEN_NEW_THREADS_CREATION)
            time.sleep(DELAY_BETWEEN_NEW_THREADS_CREATION*2)
            


def main(broker, port, broker_user, broker_pass, ttlock_client, ttlock_token):
    try:
        if not ttlock_client or not ttlock_token:
            raise ValueError('Invalid ttlock client or token.')
        
        print("Starting main loop...")
        while True:
            try:
                createClients(broker, port, broker_user, broker_pass,
                ttlock_client, ttlock_token)
                print("Current threads: {}".format(threading.active_count()))
            except Exception as exception:
                print(exception)
            time.sleep(DELAY_BETWEEN_NEW_THREADS_CREATION)

    except KeyboardInterrupt :
        print("Ending...")
        global run_flag
        run_flag = False
        for lockId, future in client_futures.items():
            print("{} thread is over!".format(future.result().getLockId()))
    except ValueError as error:
        print(error)


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
    full_cmd_arguments = sys.argv
    argument_list = full_cmd_arguments[1:]
    short_options = 'b:p:u:P:c:t:'
    long_options = ['broker=', 'port=', 'user=', 'Pass=', 'client=', 'token=']
    try:
        arguments, values = getopt.getopt(argument_list, short_options, long_options)
    except getopt.error as err:
        print (str(err))
        sys.exit(2)

    for current_argument, current_value in arguments:
        if current_argument in ("-b", "--broker"):
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

    main(broker, port, broker_user, broker_pass, ttlock_client, ttlock_token)