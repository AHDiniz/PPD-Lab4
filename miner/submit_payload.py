class SolutionMsg:
    def __init__(self, transaction_id: int, seed: int, client_id: int, *args, **kwargs) -> None:
        self.transaction_id = transaction_id
        self.seed = seed
        self.client_id = client_id

    def __str__(self) -> str:
        return "SolutionMsg(transaction_id={}, seed={}, client_id={})".format(
            self.transaction_id, self.seed, self.client_id)
