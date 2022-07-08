import hashlib
import random
from challenge_response import ChallengeResponse
from submit_payload import SubmitPayload
from seed_status import SeedStatus
from submit_status import SubmitStatus
from transaction_dao import TransactionDAO
from transaction_status import TransactionStatus
from transaction import Transaction


class TransactionBO:
    invalid_id = -1

    def __init__(self):
        self.transaction_dao = TransactionDAO()

    # start server transactions
    def start_server(self) -> Transaction:
        transaction = self.transaction_dao.create_transaction(None)
        return transaction

    # Create transaction
    def create_transaction(self) -> Transaction:
        transaction = self.transaction_dao.create_transaction(
            random.randint(1, 128))
        return transaction

    def add_transaction(self, transaction: Transaction) -> None:
        self.transaction_dao.add_transaction(transaction)

    def get_transaction(self, id) -> Transaction:
        return self.transaction_dao.get_transaction(id)

    # return the id of the transaction open for challenge
    def get_transaction_id(self) -> int:
        return self.transaction_dao.get_last_transaction().transaction_id

    # return the challenge of the transaction given by id or -1 if not found
    def get_challenge(self, transaction_id: int) -> ChallengeResponse:
        transaction: Transaction = self.transaction_dao.get_transaction(
            transaction_id)
        if transaction is None:
            return ChallengeResponse(transaction_id=transaction_id, challenge=-1)
        return ChallengeResponse(transaction_id=transaction_id, challenge=transaction.challenge)

    # return status of the transaction given by id or -1 if not found
    def get_transaction_status(self, transaction_id: int) -> int:
        transaction = self.transaction_dao.get_transaction(transaction_id)
        if transaction is None:
            return TransactionStatus.invalid_id.value

        if transaction.seed is None:
            return TransactionStatus.pendente.value

        return TransactionStatus.resolvido.value

    # submit a seed for the transaction given by id and return if it is valid or not, -1 if not found
    def verify_challenge(self, submit_payload: SubmitPayload) -> SubmitStatus:

        transaction_id: int = submit_payload.transaction_id
        seed: int = submit_payload.seed
        client_id: int = submit_payload.client_id
        transaction = self.transaction_dao.get_transaction(transaction_id)
        if transaction is None:
            return SubmitStatus.invalid_id

        if transaction.seed is not None:
            return SubmitStatus.ja_solucionado

        if (self.verify_challenge(transaction.challenge, seed)):
            # mark the transaction as solved and the winner, return valid
            transaction.seed = seed
            transaction.winner = client_id
            return SubmitStatus.valido

    # validate seed of challenge
    def verify_challenge(self, challenge: int, seed: int) -> bool:
        hash_byte = hashlib.sha1(seed.to_bytes(8, byteorder='big'))
        prefix = self.bitsof(hash_byte.digest(), challenge)

        # iterate over prefix characters to check if it is a valid seed
        if (prefix != 0):
            return False

        return True

    # get the winner of the transaction given by id, 0 if no winner or -1 if not found

    def get_winner(self, transaction_id: int) -> int:
        transaction = self.transaction_dao.get_transaction(transaction_id)
        if transaction is None:
            return self.invalid_id

        if (transaction.seed is None):
            return 0

        return transaction.winner

    # get the seed of the transaction given by id, None if not found
    def get_seed(self, transaction_id: int) -> SeedStatus:
        transaction = self.transaction_dao.get_transaction(transaction_id)
        if transaction is not None:
            return SeedStatus(self.get_transaction_status(transaction_id), transaction.seed, transaction.challenge)

    def bitsof(bt, nbits):
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
