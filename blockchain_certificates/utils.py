'''
Utility functions: conversions, hashing, etc.
text=equivalent utf-8 text
hex=hex string
bytes=bytes
'''
import binascii
import hashlib

'''
Convert ASCII text to hex equivalent
'''
def text_to_hex(string):
    bstring = string.encode('utf-8')
    return binascii.hexlify(bstring).decode('utf-8')

'''
Convert hex to ASCII text equivalent
'''
def hex_to_text(hex):
    bstring = binascii.unhexlify(hex)
    return bstring.decode('utf-8')

'''
Convert from bytes to hex
'''
def bytes_to_hex(bytes):
    return binascii.hexlify(bytes).decode('utf-8')

'''
Convert from hex to bytes
'''
def hex_to_bytes(hex):
    return binascii.unhexlify(hex)

'''
Get RIPEMD digest from input bytes
TODO: expand to check input and convert to bytes first?!
'''
def ripemd160(ibytes):
    ripemd_algo = hashlib.new('ripemd160')
    ripemd_algo.update(ibytes)
    return ripemd_algo.digest()

