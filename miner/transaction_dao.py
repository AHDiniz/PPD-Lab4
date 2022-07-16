from typing import List

from tabulate import tabulate

from transaction import Transaction

transactions: List[Transaction] = []


class TransactionDAO:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # add a transaction to the list of transactions
    def create_transaction(self, challenge, generator_id) -> Transaction:
        transaction = Transaction(
            self.get_last_transaction().transaction_id + 1, challenge, None, -1, generator_id)

        self.add_transaction(transaction)
        return transaction

    # get a transaction by id
    def get_transaction(self, transaction_id: int) -> Transaction:
        for transaction in transactions:
            if transaction.transaction_id == transaction_id:
                return transaction

    # add transaction to the list of transactions
    def add_transaction(self, transaction: Transaction) -> None:
        if (not any(elem.transaction_id == transaction.transaction_id for elem in transactions)):
            transactions.append(transaction)
            self.print_transactions()

    # get last transaction
    def get_last_transaction(self) -> Transaction:
        if len(transactions) == 0:
            return Transaction(-1, 0, None, -1, -1)  # default transaction

        return transactions[-1]

    # print all transactions
    def print_transactions(self) -> None:
        print(tabulate([[transaction.transaction_id, transaction.challenge, transaction.seed, transaction.winner, transaction.generator_id]
              for transaction in transactions], headers=['Transaction ID', 'Challenge', 'Seed', 'Winner', 'Generator Client'], tablefmt='fancy_grid'))
