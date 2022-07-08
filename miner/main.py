import json
import random
import time
from typing import List
import pika
import sys
import os
from submit_payload import SubmitPayload
from transaction import Transaction

from transaction_bo import TransactionBO
from multiprocessing import cpu_count
from time import perf_counter
import threading as thrd


local_id = random.randint(1, 2000000000)

clients: List[int] = []

transaction_bo = TransactionBO()

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='miner/init')
channel.queue_declare(queue='miner/election')
channel.queue_declare(queue='miner/challenge')
channel.queue_declare(queue='miner/solution')
channel.queue_declare(queue='miner/voting')

current_challenge: Transaction = None
current_response: SubmitPayload = None
waiting_vote = False

max_clients = 4

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


def callback_init(ch, method, properties, body):
    if body not in clients:
        print("Client " + str(body) + " joined")
        clients.append(body)

    channel.basic_ack(delivery_tag=method.delivery_tag)


def callback_election(ch, method, properties, body):
    body: ElectionMsg = json.loads(body)
    if not any(elem.id == body.id for elem in election):
        print("Client " + str(body.id) + " gets number: " + str(body.vote))
        clients.append(body)

    channel.basic_ack(delivery_tag=method.delivery_tag)


def callback_challenge(ch, method, properties, body):
    global current_challenge
    current_challenge = json.loads(body)
    transaction_bo.add_transaction(current_challenge)

    channel.basic_ack(delivery_tag=method.delivery_tag)


def callback_solution(ch, method, properties, body):
    body: SubmitPayload = json.loads(body)
    challenge_response = transaction_bo.get_challenge(body.transaction_id)
    voting = VotingMsg(local_id, 0)
    if(transaction_bo.verify_challenge(challenge_response.challenge, body.seed)):
        print("Solution valid")
        voting.valid = 1
        global waiting_vote
        waiting_vote = True

    channel.basic_publish(
        exchange='', routing_key='miner/voting', body=json.dumps(voting))

    channel.basic_ack(delivery_tag=method.delivery_tag)


def callback_voting(ch, method, properties, body):
    body: VotingMsg = json.loads(body)
    if not any(elem.id == body.id for elem in election):
        voting.append(body)
        print("Client " + str(body.client_id) + " votes: " + str(body.valid))

    if (len(voting) == max_clients):
        print("Voting finished")
        if (sum(elem.valid for elem in voting) > max_clients / 2):
            print("Solution valid")
            transaction = transaction_bo.get_transaction(
                body.payload.transaction_id)
            transaction.winner = body.client_id
            transaction.seed = body.payload.seed

            if (max(election, key=lambda x: x.vote).id == local_id):
                transaction = transaction_bo.create_transaction()
                channel.basic_publish(
                    exchange='', routing_key='miner/challenge', body=json.dumps(transaction))
        else:
            print("Solution invalid")

        global waiting_vote
        waiting_vote = False

    channel.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(queue='miner/init',
                      on_message_callback=callback_init, auto_ack=True)

channel.basic_consume(queue='miner/election',
                      on_message_callback=callback_election, auto_ack=True)

channel.basic_consume(queue='miner/challenge',
                      on_message_callback=callback_challenge, auto_ack=True)

channel.basic_consume(queue='miner/solution',
                      on_message_callback=callback_solution, auto_ack=True)

channel.basic_consume(queue='miner/voting',
                      on_message_callback=callback_voting, auto_ack=True)


def main():

    print("To exit press CTRL+C")
    channel.basic_publish(
        exchange='', routing_key='miner/init', body=local_id)
    # Get ten messages and break out
    for method_frame, properties, body in channel.consume('miner/init'):

        callback_init(channel, method_frame, properties, body)

        # Escape out of the loop after 10 messages
        if method_frame.delivery_tag == max_clients:
            break

    # electing leader
    print("System initialized")

    vote = ElectionMsg()

    channel.basic_publish(
        exchange='', routing_key='miner/election', body=json.dumps(vote))
    for method_frame, properties, body in channel.consume('miner/init'):

        callback_election(channel, method_frame, properties, body)

        # Escape out of the loop after 10 messages
        if method_frame.delivery_tag == max_clients:
            break

    print("Election finished")

    if (max(election, key=lambda x: x.vote).id == local_id):
        print("I am the leader")
        transaction = transaction_bo.create_transaction()
        channel.basic_publish(
            exchange='', routing_key='miner/challenge', body=json.dumps(transaction))

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
            if (current_challenge is None or waiting_vote):
                continue

            # Reset the counter
            if (transaction_id != current_challenge.transaction_id):
                start = perf_counter()
                challenge = current_challenge.challenge
                transaction_id = current_challenge.transaction_id

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
                if (current_challenge.transaction_id != transaction_id):
                    c.release()
                    continue
                current_challenge = None

                submit = SubmitPayload(transaction_id=transaction_id,
                                       seed=seed, client_id=local_id)
                submit_json = json.dumps(submit)
                channel.basic_publish(
                    exchange='', routing_key='miner/solution', body=json.dumps(submit_json))

                end = perf_counter()

                self.__time_to_finish = end - start
                start = perf_counter()
                print("Solved transaction {} with thread {} in {} seconds".format(
                    transaction_id, self.__id, self.__time_to_finish))
                c.notify_all()
                c.release()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        channel.close()
        connection.close()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
