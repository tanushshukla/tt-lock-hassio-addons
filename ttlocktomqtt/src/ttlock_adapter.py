import paho.mqtt.client as mqtt
import time
import json
import threading
import re
import concurrent.futures
from ttlockwrapper import TTLock



DELAY_BETWEEN_NEW_THREADS_CREATION = 60
DELAY_BETWEEN_LOCK_PUBLISH_INFOS = 60



class TTLockToMqttClient(mqtt.Client):
    def __init__(self,id,ttlockClientId,ttlockToken):
        mqttClientId="lOCK-{}-{}".format(str(id),str(int(time.time())))
        super().__init__(mqttClientId)
        self.ttlockClientId = ttlockClientId
        self.ttlockToken = ttlockToken
        self.ttlock = TTLock(self.ttlockClientId,self.ttlockToken)
        self.mqttClientId=mqttClientId
        self.connected_flag=False
        self.on_connect = TTLockToMqttClient.cb_on_connect
        self.on_disconnect = TTLockToMqttClient.cb_on_disconnect
        self.on_message = TTLockToMqttClient.cb_on_message
        self.lastPublishInfo = time.time()
        self.username_pw_set(BROKER_USER, password=BROKER_PASS)
    
    def sendMensage(self,topic, msg):
        print('Client {} sending mensage "{}" to topic "{}"'.format(self.mqttClientId,msg,topic))
        self.publish(topic,msg) 

    @classmethod
    def cb_on_message(cls, client, userdata, message):
        time.sleep(1)
        print("Client {} message received: {}".format(client.mqttClientId,str(message.payload.decode("utf-8"))))
        client.handleMessage(message)

    @classmethod
    def cb_on_disconnect(cls, client, userdata, rc):
        client.connected_flag=False #set flag
        print("Client {} disconnected!".format(client.mqttClientId))

    @classmethod
    def cb_on_connect(cls,client, userdata, flags, rc):
        if rc==0:
            client.connected_flag=True #set flag
            print("Client {} connected OK!".format(client.mqttClientId))
            client.subscribe(client.COMMAND_TOPIC)
            client.sendDiscoveryMsgs()
        else:
            print("Client {} Bad connection Returned code= {}".format(client.mqttClientId,rc))    

class TTLockToMqttClientLock(TTLockToMqttClient):

    def __init__(self,lock,gateway,ttlockClientId,ttlockToken):
        self.lock = lock
        self.gateway = gateway
        self.DISCOVERY_LOCK_TOPIC = 'test/lock/ttlock/{}_lock/config'.format(self.getLockId())
        self.DISCOVERY_SENSOR_TOPIC = 'test/sensor/ttlock/{}_state/config'.format(self.getLockId())
        self.DISCOVERY_BINARY_SENSOR_TOPIC = 'test/binary_sensor/ttlock/{}_battery/config'.format(self.getLockId())
        self.BATTERY_LEVEL_SENSOR_TOPIC = 'ttlocktomqtt/{}/battery'.format(self.getLockId())
        self.COMMAND_TOPIC = 'ttlocktomqtt/{}/command'.format(self.getLockId())
        self.STATE_SENSOR_TOPIC = 'ttlocktomqtt/{}/state'.format(self.getLockId())
        self.DISCOVERY_STATE_SENSOR_PAYLOAD = '{{"device_class": "lock", "name": "{}", "state_topic": "{}", "value_template": "{{ value_json.lock}}", "uniq_id":"{}_state","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}}, "via_device":"{}" }}'
        self.DISCOVERY_LOCK_PAYLOAD = '{{"name": "{}", "command_topic": "{}", "state_topic": "{}", "value_template": "{{ value_json.command}}", "state_locked":"off", "state_unlocked":"on" , "uniq_id":"{}_lock","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}}, "via_device":"{}" }}'
        self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD = '{{"device_class": "battery", "name": "{}", "state_topic": "{}", "unit_of_measurement": "%", "value_template": "{{ value_json.battery}}", "uniq_id":"{}_battery","device":{{"identifiers":["{}"],"connections":[["mac","{}"]]}}, "via_device":"{}" }}'
        self.STATE_PAYLOAD = '{{"lock": "{}"}}'
        self.COMMAND_PAYLOAD = '{{"command": "{}"}}'
        self.BATTERY_LEVEL_PAYLOAD = '{{"battery": {}}}'
        
        super().__init__(self.getLockId(),ttlockClientId,ttlockToken)

    def getName(self):
        return self.lock.get('lockAlias')

    def getLockId(self):
        return self.lock.get('lockId')
    
    def getMac(self):
        return self.lock.get('lockMac')

    def getGatewayId(self):
        return self.gateway.get('gatewayId')
    
    def handleMessage(self,message):
        result = False
        command = str(message.payload.decode("utf-8"))
        if command=="LOCK":
            result = self.ttlock.lock()
        elif command=="UNLOCK":
            result = self.ttlock.unlock()
        else:
            print('Invalid command.')
            return
        if not result:
            #todo: send unavaible msg
            return
        self.sendLockState()    


    def publishInfos(self):
        print("Time elapsed since last info send for {} lock: {}".format(self.getLockId(),time.time()-self.lastPublishInfo))
        if time.time()-self.lastPublishInfo>DELAY_BETWEEN_LOCK_PUBLISH_INFOS:
            self.sendLockBatteryLevel()
            self.sendLockState()
            self.lastPublishInfo = time.time()
        
    
    def sendLockBatteryLevel(self):
        batteryLevel = self.ttlock.lock_electric_quantity(self.getLockId())
        msg = self.BATTERY_LEVEL_PAYLOAD.format(batteryLevel)
        self.sendMensage(self.BATTERY_LEVEL_SENSOR_TOPIC,msg) 
    
    def sendLockState(self):
        #Open state of lock:0-locked,1-unlocked,2-unknown
        state = self.ttlock.lock_state(self.getLockId())
        if state == 2:
            #todo: send unavaible msg
            pass
        lock_is = "on" if state else "off"
        msg = self.STATE_PAYLOAD.format(lock_is)
        self.sendMensage(self.STATE_SENSOR_TOPIC,msg) 
            
    def sendDiscoveryMsgs(self):
        print('Sending discoveries msgs...')
        msg = self.DISCOVERY_BATTERY_LEVEL_SENSOR_PAYLOAD.format(self.getName(),self.BATTERY_LEVEL_SENSOR_TOPIC,self.getLockId(),self.getLockId(),self.getMac(),self.getGatewayId())
        self.sendMensage(self.DISCOVERY_SENSOR_TOPIC,msg) 
        msg = self.DISCOVERY_STATE_SENSOR_PAYLOAD.format(self.getName(),self.STATE_SENSOR_TOPIC,self.getLockId(),self.getLockId(),self.getMac(),self.getGatewayId())
        self.sendMensage(self.DISCOVERY_BINARY_SENSOR_TOPIC,msg) 
        msg = self.DISCOVERY_LOCK_PAYLOAD.format(self.getName(),self.COMMAND_TOPIC,self.STATE_SENSOR_TOPIC,self.getLockId(),self.getLockId(),self.getMac(),self.getGatewayId())
        self.sendMensage(self.DISCOVERY_LOCK_TOPIC,msg) 


def client_loop(lock,gateway,keepalive=DELAY_BETWEEN_NEW_THREADS_CREATION,loop_delay=1,run_forever=False):
    ttlockToMqttClient = TTLockToMqttClientLock(lock,gateway,TTLOCK_CLIENTID,TTLOCK_TOKEN)
    print("Created TTlock Mqtt Client for lockid: {}".format(ttlockToMqttClient.mqttClientId))
    bad_connection=0
    ttlockToMqttClient.connect(BROKER,PORT,keepalive)
    while run_flag: #loop
        ttlockToMqttClient.loop(1.0)
        if ttlockToMqttClient.connected_flag:
            ttlockToMqttClient.publishInfos()
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
            if lock.get('lockId') in client_futures.keys() and not client_futures.get(lock.get('lockId')).done():
                print( 'Lock {} mqtt client already created...'.format(lock.get('lockId')))
                return
           
            client_futures[lock.get('lockId')] = executor.submit(client_loop,lock,gateway,60)


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
    for lockId,future in client_futures.items():
        print("{} thread is over!".format(future.result().getLockId()))

   





