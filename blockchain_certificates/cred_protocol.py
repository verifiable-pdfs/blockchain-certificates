'''
Functions related to the creation of the OP_RETURN bytes in accordance
to CRED meta-protocol for issuing/revoking certificates
on the blockchain.
'''
from blockchain_certificates import utils

# Allowed operators -- 2 bytes available
operators = {
    'op_issue'            : b'\x00\x04',
    'op_revoke_batch'     : b'\x00\x08',
    'op_revoke_creds'     : b'\x00\x0c',
    'op_revoke_address'   : b'\xff\x00'
}

'''
Creates CRED protocol's issue certificates command
'''
def issue_cmd(issuer_identifier, merkle_root):
    bstring = (_create_header() + operators['op_issue'] +
               _str_to_8_chars(issuer_identifier).encode('utf-8') +
               utils.hex_to_bytes(merkle_root))
    return bstring


'''
Creates CRED protocol's revoke certificates batch command
'''
def revoke_batch_cmd(txid):
    bstring = (_create_header() + operators['op_revoke_batch'] +
               utils.hex_to_bytes(txid))
    return bstring


'''
Creates CRED protocol's revoke certificates command
'''
def revoke_creds_cmd(txid, cred_hash1, cred_hash2=None):
    bstring = (_create_header() + operators['op_revoke_creds'] +
               utils.hex_to_bytes(txid) +
               utils.ripemd160(cred_hash1))

    if cred_hash2:
        bstring += utils.ripemd160(cred_hash2)

    return bstring


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
    0001=v0.1 - 0101=v1.1 - 000a=v0.10
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
Parses op_return (hex) to create a python dictionary for easy access.
Dictionary contains:
version:
cmd: op_issue | op_revoke_batch | op_revoke_creds | op_revoke_address
data:
  for op_issue it has -> issuer_identifier, merkle_root
  for op_revoke_batch it has -> txid
  for op_revoke_creds it has -> txid, [hashes]
  for op_revoke_address it has -> hash
'''
def parse_op_return_hex(hex_data):
    data_dict = {}
    # if op_return starts with CRED it is using the meta-protocol
    if hex_data.startswith(utils.text_to_hex('CRED')):
        # Structure in bytes/hex: 4 + 2 + 2 + 32 bytes = 8 + 4 + 4 + 64 in string hex
        # TODO in the future could check version_hex and act depending on version
        data_dict['version'] = hex_data[8:12]
        data_dict['cmd'] = hex_data[12:16]
        data_dict['data'] = {}
        if data_dict['cmd'] == hex_op('op_issue'):
            data_dict['data']['issuer_identifier'] = hex_data[16:32]
            data_dict['data']['merkle_root'] = hex_data[32:96]
        elif data_dict['cmd'] == hex_op('op_revoke_batch'):
            data_dict['data']['txid'] = hex_data[16:80]
        elif data_dict['cmd'] == hex_op('op_revoke_creds'):
            data_dict['data']['txid'] = hex_data[16:80]
            data_dict['data']['hashes'] = []
            data_dict['data']['hashes'].append(hex_data[80:120])
            if len(hex_data) > 120:
                data_dict['data']['hashes'].append(hex_data[120:160])
        elif data_dict['cmd'] == hex_op('op_revoke_address'):
            data_dict['data']['hash'] = hex_data[16:56]
        else:
            return None

    else:
        return None

    return data_dict

'''
Get ASCII hex of operators
'''
def hex_op(op):
    return utils.bytes_to_hex(operators[op])

