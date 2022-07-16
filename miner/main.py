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
from tabulate import tabulate

transaction_bo = TransactionBO()

threads = []

submit_lock = thrd.Condition()

waiting_vote = False

clients_needed = 4

init_routing_key = 'miner/init'
init_finished_routing_key = 'miner/init_finished'
election_routing_key = 'miner/election'
challenge_routing_key = 'miner/challenge'
solution_routing_key = 'miner/solution'
voting_routing_key = 'miner/voting'


class ClientMsg:
    def __init__(self, id, *args, **kwargs):
        self.id = id
        self.leader = False

    def __eq__(self, other):
        if isinstance(other, ClientMsg):
            return self.id == other.id
        return False


local_client = ClientMsg(random.randint(1, 2000000000))

clients: List[ClientMsg] = []


class ElectionMsg:
    def __init__(self, id, vote, *args, **kwargs) -> None:
        self.id = id
        self.vote = vote

    def __eq__(self, other):
        if isinstance(other, ElectionMsg):
            return self.id == other.id
        return False


election: List[ElectionMsg] = []


class VotingMsg:
    def __init__(self, voter: int, valid: int, transaction_id: int, seed: int, challenger: int, *args, **kwargs) -> None:
        self.voter = voter
        self.valid = valid
        self.transaction_id = transaction_id
        self.seed = seed
        self.challenger = challenger

    def __eq__(self, other):
        if isinstance(other, VotingMsg):
            return self.voter == other.voter
        return False

    def __str__(self) -> str:
        return f'VotingMsg(voter={self.voter}, valid={self.valid}, transaction_id={self.transaction_id}, seed={self.seed}, challenger={self.challenger})'


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
            exchange=init_finished_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=election_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=challenge_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=solution_routing_key, exchange_type='fanout')
        channel.exchange_declare(
            exchange=voting_routing_key, exchange_type='fanout')

        queue_name = init_routing_key + '_client_' + \
            str(local_client.id) + '_thread_' + \
            str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=init_routing_key,
                           queue=queue_name, routing_key=init_routing_key)
        channel.basic_consume(on_message_callback=self.callback_init,
                              queue=queue_name, auto_ack=True)

        queue_name = election_routing_key + '_client_' + \
            str(local_client.id) + '_thread_' + \
            str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=election_routing_key,
                           queue=queue_name, routing_key=election_routing_key)
        channel.basic_consume(on_message_callback=self.callback_election,
                              queue=queue_name, auto_ack=True)

        queue_name = challenge_routing_key + '_client_' + \
            str(local_client.id) + '_thread_' + \
            str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=challenge_routing_key,
                           queue=queue_name, routing_key=challenge_routing_key)
        channel.basic_consume(on_message_callback=self.callback_challenge,
                              queue=queue_name, auto_ack=True)

        queue_name = solution_routing_key + '_client_' + \
            str(local_client.id) + '_thread_' + \
            str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=solution_routing_key,
                           queue=queue_name, routing_key=solution_routing_key)
        channel.basic_consume(on_message_callback=self.callback_solution,
                              queue=queue_name, auto_ack=True)

        queue_name = voting_routing_key + '_client_' + \
            str(local_client.id) + '_thread_' + \
            str(random.randint(1, 2000000000))
        channel.queue_declare(queue=queue_name, exclusive=True)
        channel.queue_bind(exchange=voting_routing_key,
                           queue=queue_name, routing_key=voting_routing_key)
        channel.basic_consume(on_message_callback=self.callback_voting,
                              queue=queue_name, auto_ack=True)

        self.connection = connection
        self.channel = channel

    def callback_init(self, ch, method, properties, body):
        if (len(clients) == clients_needed):
            return

        body = json.loads(body.decode("utf-8"))
        body = ClientMsg(**body)

        if not body in clients:
            print("Client " + str(body.id) + " joined")
            clients.append(body)

    def callback_election(self, ch, method, properties, body):
        body = json.loads(body.decode("utf-8"))
        body = ElectionMsg(**body)

        if (len(election) == clients_needed):
            return

        sender = ClientMsg(body.id)

        if not sender in clients:
            print("Client " + str(sender.id) +
                  " tried to send a message without joining")
            return

        if not body in election:
            print("Client " + str(body.id) +
                  " gets number: " + str(body.vote))
            election.append(body)

    def callback_challenge(self, ch, method, properties, body):

        body = json.loads(body.decode("utf-8"))
        body = Transaction(**body)
        try:
            sender = clients[clients.index(ClientMsg(body.generator_id))]
            if not sender.leader:

                print("Client " + str(sender.id) +
                      " is not the leader")
                return
        except ValueError:
            print("Couldn't find Client " + str(body.generator_id))
            return

        print("Transaction " + str(body.transaction_id) +
              " received with challenge: " + str(body.challenge))

        transaction_bo.add_transaction(body)

    def callback_solution(self, ch, method, properties, body):
        body = json.loads(body.decode("utf-8"))
        body = SolutionMsg(**body)

        sender = ClientMsg(body.client_id)
        if not sender in clients:
            print("Client " + str(sender.id) +
                  " tried to send a message without joining")
            return
        voting = VotingMsg(local_client.id, 0, body.transaction_id,
                           body.seed, body.client_id)

        validation = transaction_bo.validate_challenge(body)
        if(validation == SubmitStatus.valido):
            voting.valid = 1
            global waiting_vote
            waiting_vote = True

        self.channel.basic_publish(
            exchange=voting_routing_key,  routing_key=voting_routing_key, body=json.dumps(voting, indent=4, cls=CustomEncoder))

    def callback_voting(self, ch, method, properties, body):
        if (len(self.voting) == clients_needed):
            return

        body = json.loads(body.decode("utf-8"))
        voting_msg = VotingMsg(**body)

        sender = ClientMsg(voting_msg.voter)
        if not sender in clients:
            print("Client " + str(sender.id) +
                  " tried to send a message without joining")
            return

        if not voting_msg in self.voting:
            self.voting.append(voting_msg)

        if (len(self.voting) == clients_needed):
            result_voting = sum(
                elem.valid for elem in self.voting) > clients_needed / 2
            print("All clients voted, result is " + str(result_voting))
            self.voting.sort(key=lambda x: x.voter)
            print(tabulate([[vote.voter, 'Valid' if vote.valid else 'Invalid', vote.transaction_id, vote.seed, vote.challenger]
                            for vote in self.voting], headers=['Voter', 'Vote', 'Transaction', 'Seed', 'Challenger'], tablefmt='fancy_grid'))
            if (result_voting):
                print("Solution valid")

                transaction = transaction_bo.get_transaction(
                    voting_msg.transaction_id)
                transaction.winner = voting_msg.challenger
                transaction.seed = voting_msg.seed
                if (local_client.leader):
                    transaction = transaction_bo.create_transaction(
                        local_client.id)

                    self.channel.basic_publish(
                        exchange=challenge_routing_key, routing_key=challenge_routing_key, body=json.dumps(transaction, indent=4, cls=CustomEncoder))

            else:
                print("Solution invalid")

            self.voting = []
            global waiting_vote
            waiting_vote = False

    def run(self):
        self.channel.start_consuming()


def main():

    print("To exit press CTRL+C")
    print("Initializing miner for client " + str(local_client.id))
    publisher = Publisher()
    channel = publisher.channel
    while len(clients) < clients_needed:
        print("Wait for clients to finish initialization")
        channel.basic_publish(
            exchange=init_routing_key,  routing_key=init_routing_key, body=json.dumps(local_client, indent=4, cls=CustomEncoder))
        time.sleep(1)

    print("System initialized")

    # electing leader
    vote = ElectionMsg(local_client.id, random.randint(1, 2000000000))

    while len(election) < clients_needed:
        print("Waiting for election")
        channel.basic_publish(
            exchange=init_routing_key,  routing_key=init_routing_key, body=json.dumps(local_client, indent=4, cls=CustomEncoder))
        channel.basic_publish(
            exchange=election_routing_key,  routing_key=election_routing_key, body=json.dumps(vote, indent=4, cls=CustomEncoder))
        time.sleep(1)

    clients.sort(key=lambda x: x.id, reverse=True)
    election.sort(key=lambda x: x.id, reverse=True)
    print("Election Result:")
    print(tabulate([[vote.id, vote.vote]
                    for vote in election], headers=['Id', 'Vote'], tablefmt='fancy_grid'))

    leader = max(election, key=lambda x: x.vote)
    leader = clients[clients.index(ClientMsg(leader.id))]
    leader. leader = True

    print("All clients joined, leader is " + str(leader.id))
    print(tabulate([[client.id, 'Leader' if client.leader else 'Client']
                    for client in clients], headers=['Id', 'Leader'], tablefmt='fancy_grid'))

    if (leader.id == local_client.id):
        local_client.leader = True
        transaction = transaction_bo.create_transaction(local_client.id)
        channel.basic_publish(
            exchange=challenge_routing_key,  routing_key=challenge_routing_key, body=json.dumps(transaction, indent=4, cls=CustomEncoder))

    print("Running for client id: " + str(local_client.id))

    max_threads = 1
    for i in range(0, max_threads):
        seed_calculator = SeedCalculator(i)
        threads.append(seed_calculator)

        seed_calculator.start()


class SeedCalculator(thrd.Thread):
    def __init__(self, id):
        thrd.Thread.__init__(self)
        self.__time_to_finish = 0
        self.start_time = 0
        self.end_time = 0
        self.__id = id
        self.publisher = Publisher()

    def run(self):

        print("SeedCalculator {} started".format(self.__id))
        self.start_time = perf_counter()
        transaction_id = -1
        challenge = -1
        while (True):
            global waiting_vote
            transaction = transaction_bo.get_current_transaction()

            if (transaction.transaction_id != transaction_id):
                self.start_time = perf_counter()
                transaction_id = transaction.transaction_id
                challenge = transaction.challenge

            if (waiting_vote or transaction_id == -1):
                continue

            # Calculate the seed
            seed = random.randint(0, 2000000000)
            valid_seed = transaction_bo.verify_seed(
                challenge, seed)

            # iterate over prefix characters to check if it is a valid seed
            if (not valid_seed):
                continue
            else:
                # if the prefix is all zeros, the seed is valid and we can break and submit the solution
                submit_lock.acquire()
                if (waiting_vote):
                    submit_lock.release()
                    continue

                waiting_vote = True

                submit = SolutionMsg(transaction_id=transaction_id,
                                     seed=seed, client_id=local_client.id)
                submit_json = json.dumps(submit, indent=4, cls=CustomEncoder)

                self.publisher.channel.basic_publish(
                    exchange=solution_routing_key,  routing_key=solution_routing_key, body=submit_json)

                self.end_time = perf_counter()
                self.__time_to_finish = self.end_time - self.start_time
                print("Solved transaction {} with thread {} in {} seconds".format(
                    transaction_id, self.__id, self.__time_to_finish))
                submit_lock.release()

            transaction = transaction_bo.get_current_transaction()


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

    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
            raise
