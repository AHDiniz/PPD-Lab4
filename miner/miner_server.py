import time
from custom_encoder import CustomEncoder
from submit_payload import SubmitPayload
from submit_status import SubmitStatus
import paho.mqtt.client as mqtt
import json


from transaction_bo import TransactionBO

transaction_bo = TransactionBO()

mqttBroker = "127.0.0.1"
#mqttBroker = "broker.emqx.io"
client = mqtt.Client("Server")
client.connect(mqttBroker)

transaction_bo.start_server()
print("Server is running")

client.loop_start()
client.subscribe(topic="ppd/seed", qos=1)

challenge_out = json.dumps(transaction_bo.get_challenge(
    transaction_id=transaction_bo.get_transaction_id()), indent=4, cls=CustomEncoder)

client.publish(topic="ppd/challenge",
               payload=challenge_out, retain=True, qos=1)


def on_message(client, userdata, message):
    print("Incoming message...")
    data_in = json.loads(message.payload.decode("utf-8"))
    print(data_in)
    data_in = SubmitPayload(**data_in)
    submit_status = transaction_bo.verify_challenge(data_in)
    if (submit_status == SubmitStatus.valido):
        result_out = message.payload
        client.publish("ppd/result",  payload=result_out)
        challenge_out = json.dumps(transaction_bo.get_challenge(
            transaction_id=transaction_bo.get_transaction_id()), indent=4, cls=CustomEncoder)
        client.publish("ppd/challenge",  payload=challenge_out,
                       retain=True, qos=1)


client.on_message = on_message


while(True):
    time.sleep(1)
