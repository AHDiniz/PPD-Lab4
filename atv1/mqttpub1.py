from custom_encoder import CustomEncoder
import paho.mqtt.client as mqtt
from random import randrange, uniform
import time
import json


class LightSensor:
    def __init__(self, light1, light2):
        self.light1 = light1
        self.light2 = light2


mqttBroker = "127.0.0.1"
#mqttBroker = "broker.emqx.io"
client = mqtt.Client("Node_1")
client.connect(mqttBroker)
while True:
    randNumber = uniform(100.0, 150.0)
    data = LightSensor(randNumber, randNumber + randrange(1, 10))
    data_json = json.dumps(data, indent=4, cls=CustomEncoder)
    client.publish("rsv/light", data_json)
    print("Just published " + data_json + " to topic rsv/light")
    time.sleep(1)
