# define a class for transactions
class Transaction:
    # constructor for the class
    def __init__(self, transaction_id: int, challenge: int, seed: str, winner: int, *args, **kwargs) -> None:
        self.transaction_id = transaction_id
        self.challenge = challenge
        self.seed = seed
        self.winner = winner

    # override the equals method
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Transaction):
            return False
        return frozenset(self.transaction_id) == frozenset(__o.transaction_id)

    # override the hash method
    def __hash__(self) -> int:
        return hash(frozenset(self.transaction_id))
