import time
import paho.mqtt.client as mqtt
import json


class TempSensor:
    def __init__(self, temp1, temp2, *args, **kwargs) -> None:
        self.temp1 = temp1
        self.temp2 = temp2


class LightSensor:
    def __init__(self, light1, light2, *args, **kwargs):
        self.light1 = light1
        self.light2 = light2


def temperature_message(data_in):
    data_in = TempSensor(**data_in)
    print("received message: ", data_in.temp1, ", ",
          data_in.temp2)


def light_message(data_in):
    data_in = LightSensor(**data_in)
    print("received message: ", data_in.light1, ", ",
          data_in.light2)


def on_message(client, userdata, message):
    data_in = json.loads(message.payload.decode("utf-8"))

    print("Topic: ", message.topic)
    if (message.topic == "rsv/temp"):
        temperature_message(data_in)
    elif (message.topic == "rsv/light"):
        light_message(data_in)
    print("---------------------------------")


mqttBroker = "127.0.0.1"
#mqttBroker = "broker.emqx.io"
client = mqtt.Client("Node_3")
client.connect(mqttBroker)
client.loop_start()
client.subscribe("rsv/temp")
client.subscribe("rsv/light")
client.on_message = on_message
time.sleep(3000)
client.loop_stop()
