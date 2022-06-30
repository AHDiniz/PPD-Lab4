from enum import Enum


class TransactionStatus(Enum):
    resolvido = 0
    pendente = 1
    invalid_id = -1
