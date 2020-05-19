
import paho.mqtt.client as mqtt
import time
import json
import threading
import re
from ttlockwrapper import TTLock





DELAY_BETWEEN_NEW_THREADS_CREATION = 60
DELAY_BETWEEN_BATTERY_SENDS = 60


class TTLockToMqttClient(mqtt.Client):
    def __init__(self,mqttClientId,ttlockClientId,ttlockToken):
        super().__init__(mqttClientId)
        self.mqttClientId=mqttClientId
        self.ttlockClientId = ttlockClientId
        self.ttlockToken = ttlockToken
        self.connected_flag=False
        self.run_flag=True
        self.on_connect = TTLockToMqttClient.cb_on_connect
        self.on_disconnect = TTLockToMqttClient.cb_on_disconnect
        self.on_message = TTLockToMqttClient.cb_on_message
        self.username_pw_set(BROKER_USER, password=BROKER_PASS)
    
    def sendMensage(self,topic, msg):
        print('Client {} sending mensage "{}" to topic "{}"'.format(self.mqttClientId,msg,topic))
        self.publish(topic,msg) 

    @classmethod
    def cb_on_message(cls, client, userdata, message):
        time.sleep(1)
        print("message received",str(message.payload.decode("utf-8")))

    @classmethod
    def cb_on_disconnect(cls, client, userdata, rc):
        client.connected_flag=False #set flag
        print("Client {} disconnected!".format(clientId.mqttClientId))

    @classmethod
    def cb_on_connect(cls,client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True #set flag
            print("Client {} connected OK!".format(clientId.mqttClientId))
            client.sendDiscoveryMsgs()
        else:
            print("Client {} Bad connection Returned code= {}".format(clientId.mqttClientId,rc))    


class TTLockToMqttClientLock(TTLockToMqttClient):

    def __init__(self,lockId,ttlockClientId,ttlockToken):
        mqttClientId="lOCK-{}-{}".format(str(lockId),str(int(time.time())))
        super().__init__(mqttClientId,ttlockClientId,ttlockToken)
        self.lockId = lockId
        self.lastBatterySending = time.time()
    
    def sendLockBatteryLevel(self):
        if time.time()-self.lastBatterySending>DELAY_BETWEEN_BATTERY_SENDS:
            batteryLevel = TTLock(self.ttlockClientId,self.ttlockToken).lock_electric_quantity(self.lockId)
            msg = BATTERY_LEVEL_PAYLOAD.format(self.lockId,batteryLevel)
            self.sendMensage(BATTERY_LEVEL_SENSOR_TOPIC,msg) 
            self.lastBatterySending = time.time()
    
    def sendDiscoveryMsgs(self):
        msg = DISCOVERY_PAYLOAD.format(self.lockId,BATTERY_LEVEL_SENSOR_TOPIC)
        self.sendMensage(DISCOVERY_BATTERY_LEVEL_SENSOR_TOPIC,msg) 

class GatewayTTLockToMqttClient(TTLockToMqttClient):
    def __init__(self,gatewayId,ttlockClientId,ttlockToken):
        mqttClientId="GATEWAY-{}-{}".format(str(gatewayId),str(int(time.time())))
        super().__init__(mqttClientId,ttlockClientId,ttlockToken)
        self.gatewayId = gatewayId

def client_loop(ttlockToMqttClient,keepalive=DELAY_BETWEEN_NEW_THREADS_CREATION,loop_delay=1,run_forever=False):
    """runs a loop that will auto reconnect and subscribe to topics
    pass topics as a list of tuples. You can pass a function to be
    called at set intervals determined by the loop_delay
    """
    ttlockToMqttClient.connect(BROKER,PORT,keepalive)

    while ttlockToMqttClient.run_flag: #loop
        ttlockToMqttClient.loop(1.0)
        if ttlockToMqttClient.connected_flag:
            ttlockToMqttClient.sendLockBatteryLevel()

    print("disconnecting from: {}".format(BROKER))
    if ttlockToMqttClient.connected_flag:
        ttlockToMqttClient.disconnect()


def createConnections():
    ttlock = TTLock(TTLOCK_CLIENTID,TTLOCK_TOKEN)
    for gateway in ttlock.get_gateway_generator():
        for lock in ttlock.get_locks_per_gateway_generator(gateway.get("gatewayId")):
            if lock.get('lockId') in clients.keys():
                print( 'Lock {} mqtt client already created...'.format(lock.get('lockId')))
                return
            print( 'Creating TTlock Mqtt Client for lockid: {}'.format(lock.get('lockId')))
            client = TTLockToMqttClientLock(lock.get('lockId'),TTLOCK_CLIENTID,TTLOCK_TOKEN)

            clients[lock.get('lockId')]=client
            t = threading.Thread(target=client_loop,args=(client,60))
            t.start()

def removeDeadConnections():
    for clientId,client in clients.items():
        if time.time - client.lastBatterySending > DELAY_BETWEEN_BATTERY_SENDS*2:
            print('Stopping dead threading for client: {}'.format(clientId))

            clients.pop(client.get('lockId'))
            if client.connected_flag:
                client.connected_flag=False

clients=dict()

print("Starting main loop...")
try:
    while True:
        removeDeadConnections()
        createConnections()
        print("Current threads: {}".format(threading.active_count()))
        time.sleep(DELAY_BETWEEN_NEW_THREADS_CREATION)
except KeyboardInterrupt:
    print("Ending...")
    for clientId,client in clients.items():
        print('Stopping threading for client: {}'.format(clientId))
        client.run_flag=False

time.sleep(10)
   





