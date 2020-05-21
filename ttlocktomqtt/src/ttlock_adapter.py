import paho.mqtt.client as mqtt
import time
import json
import threading
import re
import concurrent.futures
from ttlockwrapper import TTLock

BROKER = '192.168.31.241'
PORT = 1883


DELAY_BETWEEN_NEW_THREADS_CREATION = 60
DELAY_BETWEEN_BATTERY_SENDS = 60
LOCK_NAME  = "TTLOCK_{}_{}"


class TTLockToMqttClient(mqtt.Client):
    def __init__(self,mqttClientId,ttlockClientId,ttlockToken):
        super().__init__(mqttClientId)
        self.ttlockClientId = ttlockClientId
        self.ttlockToken = ttlockToken
        self.ttlock = TTLock(self.ttlockClientId,self.ttlockToken)
        self.mqttClientId=mqttClientId
        self.connected_flag=False
        self.on_connect = TTLockToMqttClient.cb_on_connect
        self.on_disconnect = TTLockToMqttClient.cb_on_disconnect
        self.on_message = TTLockToMqttClient.cb_on_message
        self.on_publish = TTLockToMqttClient.cb_on_publish
        self.username_pw_set(BROKER_USER, password=BROKER_PASS)
    
    def sendMensage(self,topic, msg):
        print('Client {} sending mensage "{}" to topic "{}"'.format(self.mqttClientId,msg,topic))
        self.publish(topic,msg) 

    @classmethod
    def cb_on_publish(cls, client, userdata, message):
        print('Last send message time: {}'.format(time.time()))
        client.lastBatterySending = time.time()

    @classmethod
    def cb_on_message(cls, client, userdata, message):
        time.sleep(1)
        print("message received",str(message.payload.decode("utf-8")))

    @classmethod
    def cb_on_disconnect(cls, client, userdata, rc):
        client.connected_flag=False #set flag
        print("Client {} disconnected!".format(client.mqttClientId))

    @classmethod
    def cb_on_connect(cls,client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True #set flag
            print("Client {} connected OK!".format(client.mqttClientId))
            client.sendDiscoveryMsgs()
        else:
            print("Client {} Bad connection Returned code= {}".format(client.mqttClientId,rc))    

class TTLockToMqttClientLock(TTLockToMqttClient):

    def __init__(self,lockId,gatewayId,ttlockClientId,ttlockToken):
        self.lockName = LOCK_NAME.format(gatewayId,lockId)
        self.DISCOVERY_BATTERY_LEVEL_SENSOR_TOPIC = 'test/sensor/ttlock/{}/config'.format(self.lockName)
        self.BATTERY_LEVEL_SENSOR_TOPIC = 'ttlocktomqtt/{}/battery'.format(self.lockName)
        self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD = '{{"device_class": "battery", "name": "{}", "state_topic": "{}", "unit_of_measurement": "%", "value_template": "{{ value_json.battery}}" }}'
        self.BATTERY_LEVEL_PAYLOAD = '{{ "name": "{}", "battery": {}}}'


        mqttClientId="lOCK-{}-{}".format(str(lockId),str(int(time.time())))
        super().__init__(mqttClientId,ttlockClientId,ttlockToken)
        self.lockId = lockId
        self.lastBatterySending = time.time()
    
    def sendLockBatteryLevel(self):
        if time.time()-self.lastBatterySending>DELAY_BETWEEN_BATTERY_SENDS:
            batteryLevel = self.ttlock.lock_electric_quantity(self.lockId)
            msg = self.BATTERY_LEVEL_PAYLOAD.format(self.lockName,batteryLevel)
            self.sendMensage(self.BATTERY_LEVEL_SENSOR_TOPIC,msg) 
            
    def sendDiscoveryMsgs(self):
        msg = self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD.format(self.lockName,self.BATTERY_LEVEL_SENSOR_TOPIC)
        self.sendMensage(self.DISCOVERY_BATTERY_LEVEL_SENSOR_TOPIC,msg) 
    

def client_loop(lockId,gatewayId,keepalive=DELAY_BETWEEN_NEW_THREADS_CREATION,loop_delay=1,run_forever=False):
    ttlockToMqttClient = TTLockToMqttClientLock(lockId,gatewayId,TTLOCK_CLIENTID,TTLOCK_TOKEN)
    print("Creating TTlock Mqtt Client for lockid: {}".format(ttlockToMqttClient.mqttClientId))
    print("Starting client {} loop".format(ttlockToMqttClient.mqttClientId))
    bad_connection=0
    ttlockToMqttClient.connect(BROKER,PORT,keepalive)
    while run_flag: #loop
        ttlockToMqttClient.loop(1.0)
        if ttlockToMqttClient.connected_flag:
            ttlockToMqttClient.sendLockBatteryLevel()
        else:
            if bad_connection>5 and not run_forever:
                break
            bad_connection+=1
            time.sleep(10)

    if ttlockToMqttClient.connected_flag:
        ttlockToMqttClient.disconnect()

    return ttlockToMqttClient


def createClients():
    ttlock = TTLock(TTLOCK_CLIENTID,TTLOCK_TOKEN)
    for gateway in ttlock.get_gateway_generator():
        for lock in ttlock.get_locks_per_gateway_generator(gateway.get("gatewayId")):
            lockName = LOCK_NAME.format(gateway.get("gatewayId"),lock.get('lockId'))
            if lockName in client_futures.keys() and not client_futures.get(lockName).done():
                print( 'Lock {} mqtt client already created...'.format(lockName))
                return
           
            client_futures[lockName] = executor.submit(client_loop,lock.get('lockId'),gateway.get("gatewayId"),60)


client_futures=dict()
executor = concurrent.futures.ThreadPoolExecutor()
run_flag=True

print("Starting main loop...")
try:
    while True:
        createClients()
        print("Current threads: {}".format(threading.active_count()))
        time.sleep(DELAY_BETWEEN_NEW_THREADS_CREATION)
except KeyboardInterrupt:
    print("Ending...")
    run_flag=False
    for lockName,future in client_futures.items():
        print("{} thread is over!".format(future.result().lockName))

   





