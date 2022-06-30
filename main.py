import hashlib
import bitarray
seed = 483366386
ba = bitarray.bitarray()
hash_byte = hashlib.sha1(seed.to_bytes(8, byteorder='big'))
ba.frombytes(hash_byte.digest())

print(ba[0:6])