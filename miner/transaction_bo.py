import hashlib
import random
from submit_payload import SolutionMsg
from submit_status import SubmitStatus
from transaction_dao import TransactionDAO
from transaction import Transaction


class TransactionBO:
    invalid_id = -1

    def __init__(self):
        self.transaction_dao = TransactionDAO()

    # Create transaction
    def create_transaction(self) -> Transaction:
        transaction = self.transaction_dao.create_transaction(
            random.randint(1, 128))
        return transaction

    def add_transaction(self, transaction: Transaction) -> None:
        self.transaction_dao.add_transaction(transaction)

    def get_transaction(self, id) -> Transaction:
        return self.transaction_dao.get_transaction(id)

    # submit a seed for the transaction given by id and return if it is valid or not, -1 if not found
    def validate_challenge(self, submit_payload: SolutionMsg) -> SubmitStatus:

        transaction_id: int = submit_payload.transaction_id
        seed: int = submit_payload.seed
        client_id: int = submit_payload.client_id
        transaction = self.transaction_dao.get_transaction(transaction_id)
        if transaction is None:
            return SubmitStatus.invalid_id

        if transaction.seed is not None:
            return SubmitStatus.ja_solucionado

        if (self.verify_seed(transaction.challenge, seed)):
            # mark the transaction as solved and the winner, return valid
            transaction.seed = seed
            transaction.winner = client_id
            return SubmitStatus.valido

    # validate seed of challenge
    def verify_seed(self, challenge: int, seed: int) -> bool:
        hash_byte = hashlib.sha1(seed.to_bytes(8, byteorder='big'))
        prefix = self.bitsof(hash_byte.digest(), challenge)

        # iterate over prefix characters to check if it is a valid seed
        if (prefix != 0):
            return False

        return True

    def bitsof(self, bt, nbits):
        # Directly convert enough bytes to an int to ensure you have at least as many bits
        # as needed, but no more
        neededbytes = (nbits+7)//8
        if neededbytes > len(bt):
            raise ValueError(
                "Require {} bytes, received {}".format(neededbytes, len(bt)))
        i = int.from_bytes(bt[:neededbytes], 'big')
        # If there were a non-byte aligned number of bits requested,
        # shift off the excess from the right (which came from the last byte processed)
        if nbits % 8:
            i >>= 8 - nbits % 8
        return i
