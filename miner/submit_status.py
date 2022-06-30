from enum import Enum


class SubmitStatus(Enum):
    valido = 1
    invalido = 0
    ja_solucionado = 2
    invalid_id = -1
