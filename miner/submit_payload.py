class SolutionMsg:
    def __init__(self, transaction_id: int, seed: int, client_id: int, *args, **kwargs) -> None:
        self.transaction_id = transaction_id
        self.seed = seed
        self.client_id = client_id
