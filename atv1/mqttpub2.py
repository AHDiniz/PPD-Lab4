import paho.mqtt.client as mqtt
from random import randrange, uniform
import time
import json
from custom_encoder import CustomEncoder


class TempSensor:
    def __init__(self, temp1, temp2) -> None:
        self.temp1 = temp1
        self.temp2 = temp2


mqttBroker = "127.0.0.1"
#mqttBroker = "broker.emqx.io"
client = mqtt.Client("Node_2")
client.connect(mqttBroker)
while True:
    randNumber = randrange(15, 25)
    data = TempSensor(randNumber, randNumber + randrange(1, 5))
    data_json = json.dumps(data, indent=4, cls=CustomEncoder)
    client.publish("rsv/temp", data_json)
    print("Just published " + data_json + " to topic rsv/temp")
    time.sleep(1)
