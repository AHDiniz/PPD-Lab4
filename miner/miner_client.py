import hashlib
import time
import json
import random
import paho.mqtt.client as mqtt
import threading as thrd
from custom_encoder import CustomEncoder
from challenge_response import ChallengeResponse
from submit_payload import SubmitPayload
from multiprocessing import cpu_count
from time import perf_counter

c = thrd.Condition()
current_challenge = None

def bitsof(bt, nbits):
    # Directly convert enough bytes to an int to ensure you have at least as many bits
    # as needed, but no more
    neededbytes = (nbits+7)//8
    if neededbytes > len(bt):
        raise ValueError("Require {} bytes, received {}".format(neededbytes, len(bt))) 
    i = int.from_bytes(bt[:neededbytes], 'big')
    # If there were a non-byte aligned number of bits requested,
    # shift off the excess from the right (which came from the last byte processed)
    if nbits % 8:
        i >>= 8 - nbits % 8
    return i

class SeedCalculator(thrd.Thread):
    def __init__(self, id):
        thrd.Thread.__init__(self)
        self.__seed = 0
        self.__time_to_finish = 0
        self.__id = id

    @property
    def seed(self):
        return self.__seed

    @property
    def time_to_finish(self):
        return self.__time_to_finish

    def run(self):
        print("SeedCalculator {} started".format(self.__id))
        challenge = -1
        transaction_id = -1
        while (True):
            global current_challenge

            # Wait for a challenge
            if (current_challenge is None):
                continue

            # Reset the counter
            if (transaction_id != current_challenge.transaction_id):
                start = perf_counter()
                challenge = current_challenge.challenge
                transaction_id = current_challenge.transaction_id

            # Calculate the seed
            seed = random.randint(0, 2000000000)
            hash_byte = hashlib.sha1(seed.to_bytes(8, byteorder='big'))
            prefix = bitsof(hash_byte.digest(), challenge)

            # iterate over prefix characters to check if it is a valid seed
            if (prefix != 0):
                continue
            else:
                # if the prefix is all zeros, the seed is valid and we can break and submit the solution
                c.acquire()

                # if someone else has already submitted the solution, we need to wait for them to finish and not submit again
                if (current_challenge.transaction_id != transaction_id):
                    c.release()
                    continue
                current_challenge = None

                submit = SubmitPayload(transaction_id=transaction_id,
                                       seed=seed, client_id=client_id)
                submit_json = json.dumps(submit, indent=4, cls=CustomEncoder)
                client.publish(topic="ppd/seed", payload=submit_json)

                end = perf_counter()

                self.__time_to_finish = end - start
                start = perf_counter()
                print("Solved transaction {} with thread {} in {} seconds".format(
                    transaction_id, self.__id, self.__time_to_finish))
                c.notify_all()
                c.release()


mqttBroker = "127.0.0.1"
#mqttBroker = "broker.emqx.io"
client_id = int(time.time())
client = mqtt.Client(
    "Client " + str(client_id))
print("Running for client id: " + str(client_id))
client.connect(mqttBroker)

client.loop_start()
client.subscribe(topic="ppd/challenge")
client.subscribe(topic="ppd/result")


def on_message(client, userdata, message):
    print("Incoming message...")
    data_in = json.loads(message.payload.decode("utf-8"))

    if (message.topic == "ppd/challenge"):
        print("Challenge: ", data_in)
        data_in = ChallengeResponse(**data_in)
        c.acquire()
        global current_challenge
        current_challenge = data_in
        c.notify_all()
        c.release()
    if (message.topic == "ppd/result"):
        print("Result: ", data_in)
        data_in = SubmitPayload(**data_in)


client.on_message = on_message


def mine():

    max_threads = int(cpu_count() / 2)
    threads: SeedCalculator = []
    for i in range(0, max_threads):
        seed_calculator = SeedCalculator(i)
        threads.append(seed_calculator)

        seed_calculator.start()

    for s in threads:
        s.join()


mine()
