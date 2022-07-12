import json
import logging
import random
import time
from typing import List
import pika
import sys
import os
from custom_encoder import CustomEncoder
from submit_payload import SubmitPayload
from transaction import Transaction

from transaction_bo import TransactionBO
from time import perf_counter
import threading as thrd


local_id = random.randint(1, 2000000000)

clients: List[int] = []

transaction_bo = TransactionBO()


current_challenge: Transaction = None
current_response: SubmitPayload = None
waiting_vote = False

max_clients = 1

init_channel = 'miner/init'
election_channel = 'miner/election'
challenge_channel = 'miner/challenge'
solution_channel = 'miner/solution'
voting_channel = 'miner/voting'

c = thrd.Condition()


class ElectionMsg:
    def __init__(self) -> None:
        self.id = local_id
        self.vote = random.randint(1, 2000000000)


election: List[ElectionMsg] = []


class VotingMsg:
    def __init__(self, client_id: int, valid: int, payload: SubmitPayload) -> None:
        self.client_id = client_id
        self.valid = valid
        self.payload = payload


voting: List[VotingMsg] = []


def on_channel_open(channel):
    print("declaring channel queue")
    channel.queue_declare(queue=init_channel)
    channel.queue_declare(queue=election_channel)
    channel.queue_declare(queue=challenge_channel)
    channel.queue_declare(queue=solution_channel)
    channel.queue_declare(queue=voting_channel)
    
    channel.basic_consume(on_message_callback=callback_init,
                            queue=init_channel, auto_ack=True)
    channel.basic_consume(on_message_callback=callback_election, 
                            queue=election_channel, auto_ack=True)
    channel.basic_consume(on_message_callback=callback_challenge,
                            queue=challenge_channel, auto_ack=True)
    channel.basic_consume(on_message_callback=callback_solution, 
                            queue=solution_channel, auto_ack=True)
    channel.basic_consume(on_message_callback=callback_voting,
                            queue=voting_channel, auto_ack=True)

def on_open(connection):
    print("opening connection")
    connection.channel(on_open_callback=on_channel_open)


connection = None


def return_connection():
    global connection
    if (connection is None or connection.is_closed):
        connection = pika.SelectConnection(parameters=pika.ConnectionParameters(host='localhost'),
                                           on_open_callback=on_open)
    return connection


def callback_init(ch, method, properties, body):
    body = int(body)
    print(" [x] callback_init: received %r" % body)
    if body not in clients:
        print("Client " + str(body) + " joined")
        clients.append(body)


def callback_election(ch, method, properties, body):
    body: ElectionMsg = json.loads(body.decode("utf-8"))
    print(" [x] callback_eletction: received %r" % body)
    if not any(elem['id'] == body['id'] for elem in election):
        print("Client " + str(body["id"]) + " gets number: " + str(body["vote"]))
        election.append(body)
    print(election)


def callback_challenge(ch, method, properties, body):
    global current_challenge
    print(" [x] callback_challenge: received %r" % body)
    current_challenge = json.loads(body.decode("utf-8"))

    print("Transaction received " + str(current_challenge['transaction_id']) +
          " with challenge: " + str(current_challenge['challenge']))
    
    transaction_bo.add_transaction(current_challenge)


def callback_solution(ch, method, properties, body):
    body: SubmitPayload = json.loads(body.decode("utf-8"))
    print(" [x] callback_solution: received %r" % body)
    challenge_response = transaction_bo.get_challenge(body['transaction_id'])
    voting = VotingMsg(local_id, 0)
    if(transaction_bo.verify_challenge(challenge_response['challenge'], body['seed'])):
        print("Solution valid")
        voting.valid = 1
        global waiting_vote
        waiting_vote = True

    return_connection().channel().basic_publish(
        exchange='', routing_key=voting_channel, body=json.dumps(voting, indent=4, cls=CustomEncoder))


def callback_voting(ch, method, properties, body):
    body: VotingMsg = json.loads(body.decode("utf-8"))
    print(" [x] callback_voting: received %r" % body)
    if not any(elem['id'] == body['id'] for elem in election):
        voting.append(body)
        print("Client " + str(body['client_id']) + " votes: " + str(body['valid']))

    if (len(voting) == max_clients):
        print("Voting finished")
        if (sum(elem.valid for elem in voting) > max_clients / 2):
            print("Solution valid")
            transaction = transaction_bo.get_transaction(
                body.payload.transaction_id)
            transaction.winner = body.client_id
            transaction.seed = body.payload.seed

            if (max(election, key=lambda x: x['vote'])['id'] == local_id):
                transaction = transaction_bo.create_transaction()

                return_connection().channel().basic_publish(
                    exchange='', routing_key=challenge_channel, body=json.dumps(transaction, indent=4, cls=CustomEncoder))
        else:
            print("Solution invalid")

        global waiting_vote
        waiting_vote = False


class Consumer(thrd.Thread):
    def __init__(self):
        thrd.Thread.__init__(self)
        self.connection = pika.SelectConnection(parameters=pika.ConnectionParameters(host='localhost'),
                                                on_open_callback=on_open)

    def run(self):
        self.connection.ioloop.start()


def main():

    print("To exit press CTRL+C")
    print("Initializing miner")
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=init_channel)
    channel.queue_declare(queue=election_channel)
    channel.queue_declare(queue=challenge_channel)
    channel.queue_declare(queue=solution_channel)
    channel.queue_declare(queue=voting_channel)
    while len(clients) < max_clients:
        print("Waiting for clients")
        channel.basic_publish(
            exchange='', routing_key=init_channel, body=str(local_id))
        time.sleep(2)

    # electing leader
    print("System initialized")

    vote = ElectionMsg()

    while len(election) < max_clients:
        print("Waiting for election")
        channel.basic_publish(
            exchange='', routing_key=election_channel, body=json.dumps(vote, indent=4, cls=CustomEncoder))
        time.sleep(2)

    print("Election finished")

    if (max(election, key=lambda x: x['vote'])['id'] == local_id):
        print("I am the leader")
        transaction = transaction_bo.create_transaction()
        channel.basic_publish(
            exchange='', routing_key=challenge_channel, body=json.dumps(transaction, indent=4, cls=CustomEncoder))

    print("Running for client id: " + str(local_id))

    max_threads = 1
    threads: List[SeedCalculator] = []
    for i in range(0, max_threads):
        seed_calculator = SeedCalculator(
            i)
        threads.append(seed_calculator)

        seed_calculator.start()

    for s in threads:
        s.join()
        s.connection.close()


class SeedCalculator(thrd.Thread):
    def __init__(self, id):
        thrd.Thread.__init__(self)
        self.__seed = 0
        self.__time_to_finish = 0
        self.__id = id
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=init_channel)
        self.channel.queue_declare(queue=election_channel)
        self.channel.queue_declare(queue=challenge_channel)
        self.channel.queue_declare(queue=solution_channel)
        self.channel.queue_declare(queue=voting_channel)

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
            if (current_challenge is None or waiting_vote):
                continue

            # Reset the counter
            if (transaction_id != current_challenge['transaction_id']):
                start = perf_counter()
                challenge = current_challenge['challenge']
                transaction_id = current_challenge['transaction_id']

            # Calculate the seed
            seed = random.randint(0, 2000000000)
            valid_seed = transaction_bo.verify_challenge(
                challenge, seed)

            # iterate over prefix characters to check if it is a valid seed
            if (not valid_seed):
                continue
            else:
                # if the prefix is all zeros, the seed is valid and we can break and submit the solution
                c.acquire()

                # if someone else has already submitted the solution, we need to wait for them to finish and not submit again
                if (current_challenge['transaction_id'] != transaction_id):
                    c.release()
                    continue
                current_challenge = None

                submit = SubmitPayload(transaction_id=transaction_id,
                                       seed=seed, client_id=local_id)
                submit_json = json.dumps(submit, indent=4, cls=CustomEncoder)
                
                self.channel.basic_publish(
                    exchange='', routing_key=solution_channel, body=submit_json)

                end = perf_counter()

                self.__time_to_finish = end - start
                start = perf_counter()
                print("Solved transaction {} with thread {} in {} seconds".format(
                    transaction_id, self.__id, self.__time_to_finish))
                c.notify_all()
                c.release()


if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    # logging.basicConfig(format=format, level=logging.NOTSET,
    #                   datefmt="%H:%M:%S")
    try:
        consumer = Consumer()
        consumer.start()
        main()
        consumer.join()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            consumer.connection.close()
            sys.exit(0)
        except SystemExit:
            os._exit(0)
