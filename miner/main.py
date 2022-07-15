import json
import os
import random
import sys
import threading as thrd
import time
from time import perf_counter
from typing import List

import pika

from custom_encoder import CustomEncoder
from submit_payload import SolutionMsg
from submit_status import SubmitStatus
from transaction import Transaction
from transaction_bo import TransactionBO

transaction_bo = TransactionBO()

local_id = random.randint(1, 2000000000)

clients: List[int] = []
clients_lock = thrd.Condition()

current_challenge: Transaction = None
current_challenge_lock = thrd.Condition()

waiting_vote = False
waiting_vote_lock = thrd.Condition()

clients_needed = 10

init_routing_key = 'miner/init'
election_routing_key = 'miner/election'
challenge_routing_key = 'miner/challenge'
solution_routing_key = 'miner/solution'
voting_routing_key = 'miner/voting'


class ElectionMsg:
    def __init__(self, id, vote, *args, **kwargs) -> None:
        self.id = id
        self.vote = vote


election: List[ElectionMsg] = []


class VotingMsg:
    def __init__(self, voter: int, valid: int, transaction_id: int, seed: int, challenger: int, *args, **kwargs) -> None:
        self.voter = voter
        self.valid = valid
        self.transaction_id = transaction_id
        self.seed = seed
        self.challenger = challenger


class Publisher():
    def __init__(self):
        thrd.Thread.__init__(self)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()
        channel.exchange_declare(
            exchange=init_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=election_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=challenge_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=solution_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=voting_routing_key, exchange_type='fanout')

        self.connection = connection
        self.channel = channel


class Consumer(thrd.Thread):

    def __init__(self):
        thrd.Thread.__init__(self)
        self.voting: List[VotingMsg] = []
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))
        channel = connection.channel()

        channel.exchange_declare(
            exchange=init_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=election_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=challenge_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=solution_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=voting_routing_key, exchange_type='fanout')

        queue_name = init_routing_key + '_client_' + \
            str(local_id) + '_thread_' + str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=init_routing_key,
                           queue=queue_name, routing_key=init_routing_key)
        channel.basic_consume(on_message_callback=self.callback_init,
                              queue=queue_name, auto_ack=True)

        queue_name = election_routing_key + '_client_' + \
            str(local_id) + '_thread_' + str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=election_routing_key,
                           queue=queue_name, routing_key=election_routing_key)
        channel.basic_consume(on_message_callback=self.callback_election,
                              queue=queue_name, auto_ack=True)

        queue_name = challenge_routing_key + '_client_' + \
            str(local_id) + '_thread_' + str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=challenge_routing_key,
                           queue=queue_name, routing_key=challenge_routing_key)
        channel.basic_consume(on_message_callback=self.callback_challenge,
                              queue=queue_name, auto_ack=True)

        queue_name = solution_routing_key + '_client_' + \
            str(local_id) + '_thread_' + str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=solution_routing_key,
                           queue=queue_name, routing_key=solution_routing_key)
        channel.basic_consume(on_message_callback=self.callback_solution,
                              queue=queue_name, auto_ack=True)

        queue_name = voting_routing_key + '_client_' + \
            str(local_id) + '_thread_' + str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=voting_routing_key,
                           queue=queue_name, routing_key=voting_routing_key)
        channel.basic_consume(on_message_callback=self.callback_voting,
                              queue=queue_name, auto_ack=True)

        self.connection = connection
        self.channel = channel

    def callback_init(self, ch, method, properties, body):
        body = int(body)
        if body not in clients:
            print("Client " + str(body) + " joined")
            clients.append(body)

    def callback_election(self, ch, method, properties, body):
        body = json.loads(body.decode("utf-8"))
        body = ElectionMsg(**body)
        if not any(elem.id == body.id for elem in election):
            print("Client " + str(body.id) +
                        " gets number: " + str(body.vote))
            election.append(body)

    def callback_challenge(self, ch, method, properties, body):
        current_challenge_lock.acquire()
        global current_challenge
        body = json.loads(body.decode("utf-8"))

        print("Transaction " + str(body['transaction_id']) +
                    " received with challenge: " + str(body['challenge']))

        transaction_bo.add_transaction(Transaction(**body))
        current_challenge = Transaction(**body)

        current_challenge_lock.release()

    def callback_solution(self, ch, method, properties, body):
        waiting_vote_lock.acquire()
        body = json.loads(body.decode("utf-8"))
        body = SolutionMsg(**body)
        voting = VotingMsg(local_id, 0, body.transaction_id,
                           body.seed, body.client_id)
        if(transaction_bo.validate_challenge(body) == SubmitStatus.valido):
            voting.valid = 1
            global waiting_vote
            waiting_vote = True

        self.channel.basic_publish(
            exchange=voting_routing_key,  routing_key=voting_routing_key, body=json.dumps(voting, indent=4, cls=CustomEncoder))

        waiting_vote_lock.release()

    def callback_voting(self, ch, method, properties, body):
        body = json.loads(body.decode("utf-8"))
        voting_msg = VotingMsg(**body)

        if not any(elem.voter == voting_msg.voter for elem in self.voting):
            self.voting.append(voting_msg)
            print("Client " + str(voting_msg.voter) +
                        " votes: " + str(voting_msg.valid) +
                        " for transaction " + str(voting_msg.transaction_id) +
                        " with seed " + str(voting_msg.seed) +
                        " and challenger " + str(voting_msg.challenger))

        if (len(self.voting) == clients_needed):
            print("Voting finished")
            waiting_vote_lock.acquire()
            if (sum(elem.valid for elem in self.voting) > clients_needed / 2):
                print("Solution valid")
                current_challenge_lock.acquire()
                global current_challenge
                current_challenge = None

                transaction = transaction_bo.get_transaction(
                    voting_msg.transaction_id)
                transaction.winner = voting_msg.challenger
                transaction.seed = voting_msg.seed

                if (max(election, key=lambda x: x.vote).id == local_id):
                    transaction = transaction_bo.create_transaction()

                    self.channel.basic_publish(
                        exchange=challenge_routing_key, routing_key=challenge_routing_key, body=json.dumps(transaction, indent=4, cls=CustomEncoder))

                current_challenge_lock.release()

            else:
                print("Solution invalid")

            self.voting = []
            global waiting_vote
            waiting_vote = False
            waiting_vote_lock.release()

    def run(self):
        self.channel.start_consuming()


def main():

    print("To exit press CTRL+C")
    print("Initializing miner for client " + str(local_id))
    publisher = Publisher()
    channel = publisher.channel
    while len(clients) < clients_needed:
        print("Waiting for clients")
        channel.basic_publish(
            exchange=init_routing_key,  routing_key=init_routing_key, body=str(local_id))
        time.sleep(5)

    print("System initialized")

    # electing leader
    vote = ElectionMsg(local_id, random.randint(1, 2000000000))

    while len(election) < clients_needed:
        print("Waiting for election")
        channel.basic_publish(
            exchange=init_routing_key,  routing_key=init_routing_key, body=str(local_id))
        channel.basic_publish(
            exchange=election_routing_key,  routing_key=election_routing_key, body=json.dumps(vote, indent=4, cls=CustomEncoder))
        time.sleep(5)

    print("Election finished")

    if (max(election, key=lambda x: x.vote).id == local_id):
        print("I am the leader")
        transaction = transaction_bo.create_transaction()
        channel.basic_publish(
            exchange=challenge_routing_key,  routing_key=challenge_routing_key, body=json.dumps(transaction, indent=4, cls=CustomEncoder))

    print("Running for client id: " + str(local_id))

    max_threads = 1
    for i in range(0, max_threads):
        seed_calculator = SeedCalculator(i)
        threads.append(seed_calculator)

        seed_calculator.start()


class SeedCalculator(thrd.Thread):
    def __init__(self, id):
        thrd.Thread.__init__(self)
        self.__seed = 0
        self.__time_to_finish = 0
        self.__id = id
        self.publisher = Publisher()

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
        count = 0

        while (True):

            global waiting_vote

            if (waiting_vote):
                continue

            # Reset the counter
            if (count == 5000):
                global current_challenge
                # Wait for a challenge
                if (current_challenge is None):
                    continue
                count = 0
                current_challenge_lock.acquire()
                if (not current_challenge or transaction_id != current_challenge.transaction_id):
                    start = perf_counter()
                    challenge = current_challenge.challenge
                    transaction_id = current_challenge.transaction_id
                current_challenge_lock.release()

            # Calculate the seed
            seed = random.randint(0, 2000000000)
            valid_seed = transaction_bo.verify_seed(
                challenge, seed)

            # iterate over prefix characters to check if it is a valid seed
            if (not valid_seed):
                continue
            else:
                # if the prefix is all zeros, the seed is valid and we can break and submit the solution
                waiting_vote_lock.acquire()
                waiting_vote = True
                # if someone else has already submitted the solution, we need to not submit again
                if (not current_challenge or current_challenge.transaction_id != transaction_id):
                    continue

                submit = SolutionMsg(transaction_id=transaction_id,
                                     seed=seed, client_id=local_id)
                submit_json = json.dumps(submit, indent=4, cls=CustomEncoder)

                self.publisher.channel.basic_publish(
                    exchange=solution_routing_key,  routing_key=solution_routing_key, body=submit_json)

                end = perf_counter()

                self.__time_to_finish = end - start
                start = perf_counter()
                print("Solved transaction {} with thread {} in {} seconds".format(
                    transaction_id, self.__id, self.__time_to_finish))

                waiting_vote_lock.release()
            count = count + 1


threads: List[SeedCalculator] = []


if __name__ == '__main__':
    try:
        consumer = Consumer()
        consumer.start()
        main()

        consumer.join()
        consumer.channel.stop_consuming()
        consumer.channel.close()
        consumer.connection.close()

        for s in threads:
            s.join()
            s.publisher.channel.stop_consuming()
            s.publisher.channel.close()
            s.publisher.connection.close()

    except KeyboardInterrupt:
        print('Interrupted')
        try:
            for s in threads:
                s.publisher.channel.close()
                s.publisher.connection.close()
            consumer.channel.stop_consuming()
            consumer.channel.close()
            consumer.connection.close()
            sys.exit(0)
        except SystemExit:
            os._exit(0)
            raise
