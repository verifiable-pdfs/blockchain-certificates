'''
Functions related to the creation of the OP_RETURN bytes in accordance
to CRED meta-protocol for issuing/revoking certificates
on the blockchain.
'''
import hashlib
import binascii

# Allowed operators -- 2 bytes available
operators = {
    'op_issue'            : b'\x00\x04',
    'op_revoke_batch'     : b'\x00\x08',
    'op_revoke_certs'     : b'\x00\x0c',
    'op_revoke_address'   : b'\xff\x00'
}

'''
Creates CRED protocol's issue certificates command
'''
def issue_cmd(issuer_identifier, merkle_root):
    bstring = _create_header() + operators['op_issue'] + _str_to_8_chars(issuer_identifier).encode('utf-8') + merkle_root.encode('utf-8')
    return bstring


'''
Creates CRED protocol's revoke certificates batch command
'''
def revoke_batch_cmd(txid):
    string = _create_header() + operators['op_revoke_batch']
    return text_to_hex(string) + txid


'''
Creates CRED protocol's revoke certificates command
'''
def revoke_certs_cmd(txid, cred_hash1, cred_hash2):
    string = _create_header() + operators['op_revoke_certs']
    hashed_cred_hash1 = hashlib.sha256(cred_hash1)
    hashed_cred_hash2 = hashlib.sha256(cred_hash2)
    return text_to_hex(string) + txid + hashed_cred_hash1 + hashed_cred_hash2


'''
Creates CRED protocol's revoke address command
'''
def revoke_address_cmd(address):
    string = _create_header() + operators['op_revoke_address'] + address
    return text_to_hex(string)


'''
Creates the header for the CRED protocol. Currently consists of
'CRED' and a fixed version in hex.

Versioning: first byte major, second byte minor:
    0001=v0.1 - 01.01=v1.1 - 00.0a=v0.10
'''
def _create_header():
    major_version = 0           # max 255
    minor_version = 1           # max 255
    return b'CRED' + bytes([major_version, minor_version])


'''
Returns 8 bytes version of a (utf-8) string. If larger it removes the extra
characters. If shorter it pads with space.
'''
def _str_to_8_chars(string):
    length = len(string)
    if length < 8:
        return string.ljust(8)
    elif length > 8:
        return string[:8]
    else:
        return string


'''
Convert ASCII text to hex equivalent
'''
def text_to_hex(string): # USED??!?
    bstring = string.encode('utf-8')
    return binascii.hexlify(bstring).decode('utf-8')

'''
Convert hex to ASCII text equivalent
'''
def hex_to_text(hex): # USED???
    bstring = binascii.unhexlify(hex)
    return bstring.decode('utf-8')

