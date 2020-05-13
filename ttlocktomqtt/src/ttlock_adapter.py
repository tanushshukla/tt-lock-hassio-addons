
import paho.mqtt.client as mqtt
import time
import json
import threading
from ttlockwrapper import TTLock



BROKER = ''
PORT = 1883
BROKER_USER = ''
BROKER_PASS = ''
BATTERY_LEVEL_SENSOR_TOPIC = ''
DISCOVERY_BATTERY_LEVEL_SENSOR_TOPIC = ''

TTLOCK_CLIENTID = 'CLIENT_ID'
TTLOCK_TOKEN= 'TOKEN'

class TTLockToMqttClient():
    def __init__(self,mqttClientId,ttlockClientId,ttlockToken):
        self.mqttClient = mqtt.Client(mqttClientId)
        self.mqttClient.on_connect = on_connect
        self.mqttClient.on_disconnect = on_disconnect
        self.mqttClient.on_message = on_message
        self.ttlockClientId = ttlockClientId
        self.ttlockToken = ttlockToken
    
class TTLockToMqttClientLock(TTLockToMqttClient):
    def __init__(self,mqttClientId,lockId,ttlockClientId,ttlockToken):
        super.__init__(self,mqttClientId,ttlockClientId,ttlockToken)
        self.lockId = lockId
    
    def sendLockBatteryLevel(self):
        batteryLevel = TTLock(self.ttlockClientId,self.ttlockToken).lock_electric_quantity(self.lockId)
        self.mqttClient.publish(BATTERY_LEVEL_SENSOR_TOPIC,batteryLevel) 

class GatewayTTLockToMqttClient(TTLockToMqttClient):
    def __init__(self,mqttClientId,gatewayId,ttlockClientId,ttlockToken):
        super.__init__(self,mqttClientId,ttlockClientId,ttlockToken)
        self.gatewayId = gatewayId

def Connect(ttlockToMqttClient,broker,port,keepalive,run_forever=False):
    """Attempts connection set delay to >1 to keep trying
    but at longer intervals. If runforever flag is true then
    it will keep trying to connect or reconnect indefinetly otherwise
    gives up after 3 failed attempts"""
    connflag=False
    delay=5
    #print("connecting ",client)
    badcount=0 # counter for bad connection attempts
    while not connflag:
        print("connecting to broker "+str(broker))
        #print("connecting to broker "+str(broker)+":"+str(port))
        print("Attempts ",str(badcount))
        time.sleep(delay)
        try:
            ttlockToMqttClient.mqttClient.connect(broker,port,keepalive)
            connflag=True

        except:
            ttlockToMqttClient.mqttClient.badconnection_flag=True
            print("connection failed "+str(badcount))
            badcount +=1
            if badcount>=3 and not run_forever: 
                return -1
                raise SystemExit #give up
    
    return 0


def client_loop(ttlockToMqttClient,keepalive=60,\
             loop_delay=1,run_forever=False):
    """runs a loop that will auto reconnect and subscribe to topics
    pass topics as a list of tuples. You can pass a function to be
    called at set intervals determined by the loop_delay
    """
    ttlockToMqttClient.mqttClient.run_flag=True
    ttlockToMqttClient.mqttClient.broker=BROKER
    print("running loop ")
    ttlockToMqttClient.mqttClient.reconnect_delay_set(min_delay=1, max_delay=12)
      
    while ttlockToMqttClient.mqttClient.run_flag: #loop forever

        if ttlockToMqttClient.mqttClient.bad_connection_flag:
            break         
        if not ttlockToMqttClient.mqttClient.connected_flag:
            print("Connecting to ",BROKER)
            if Connect(ttlockToMqttClient.mqttClient,BROKER,PORT,keepalive,run_forever) !=-1:
                print("connecting to: {}".format(BROKER))
            else:#connect fails
                ttlockToMqttClient.mqttClient.run_flag=False #break
                print("quitting loop for broker: {}".format(BROKER))

        ttlockToMqttClient.mqttClient.loop(0.01)

        ttlockToMqttClient.sendLockBatteryLevel()
    
    time.sleep(1)
    print("disconnecting from: {}".format(BROKER))
    if ttlockToMqttClient.mqttClient.connected_flag:
        ttlockToMqttClient.mqttClient.disconnect()
        ttlockToMqttClient.mqttClient.connected_flag=False
    
def on_log(client, userdata, level, buf):
   print(buf)

def on_message(client, userdata, message):
   time.sleep(1)
   print("message received",str(message.payload.decode("utf-8")))

def on_connect(client, userdata, flags, rc):
    if rc==0:
        client.connected_flag=True #set flag
        for c in clients:
          if client==c["client"]:
              if c["sub_topic"]!="":
                  client.subscribe(c["sub_topic"])
          
        #print("connected OK")
    else:
        print("Bad connection Returned code=",rc)
        client.loop_stop()  

def on_disconnect(client, userdata, rc):
   client.connected_flag=False #set flag
   #print("client disconnected ok")


def Create_connections():
    ttlock = TTLock(TTLOCK_CLIENTID,TTLOCK_TOKEN)
    gateways = list(ttlock.get_gateway_generator())
    
    locks = []
    for gateway in gateways:
        locks += list(ttlock.get_locks_per_gateway_generator(gateway.get("gatewayId")))
    
    for lock in locks:
        client_id="lOCK{}-{}".format(str(lock.get('lockId')),str(int(time.time())))
        client = TTLockToMqttClientLock(client_id,lock.get('lockId'),TTLOCK_CLIENTID,TTLOCK_TOKEN)
        clients["client_id"]=client
        t = threading.Thread(target\
                =client_loop,args=(client,60))
        threads.append(t)
        t.start()


clients=dict()
threads=[]
print("Creating Connections ")
no_threads=threading.active_count()
print("current threads =",no_threads)
Create_connections()

print("All clients connected ")
no_threads=threading.active_count()
print("current threads =",no_threads)
print("starting main loop")
try:
    while True:
        time.sleep(10)
        no_threads=threading.active_count()
        print("current threads =",no_threads)
        for c in clients:
            if not c["client_id"].mqttClient.connected_flag:
                print("broker {} is disconnected".format(BROKER))
    

except KeyboardInterrupt:
    print("ending")
    for c in clients:
        c["client_id"].mqttClient.run_flag=False
time.sleep(10)
   





