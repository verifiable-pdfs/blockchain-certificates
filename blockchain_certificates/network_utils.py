'''
Functions related to network services
'''
import requests


'''
Gets all the op_return hexes stored from the specified txid (used to issue the
certificates. Get tx before issuance (for checking revoked addresses) and after
issuance (for checking revoked batches and/or certificates
'''
def get_all_op_return_hexes(address, txid, testnet=False):
    blockcypher_url = 'http://api.blockcypher.com/v1/btc'
    network = 'test3' if testnet else 'main'

    address_txs_url = '{}/{}/addrs/{}/full'.format(blockcypher_url, network, address)

    params = { 'limit': 50 }  # max tx per request on blockcypher
    address_txs = requests.get(address_txs_url, params=params).json()
    new_start_height = address_txs['txs'][-1]['block_height']
    all_relevant_txs = address_txs['txs']

    while 'hasMore' in address_txs and address_txs['hasMore']:
        params['before'] = new_start_height
        address_txs = requests.get(address_txs_url, params=params)
        new_start_height = address_txs['txs'][-1]['block_height']
        # results are newest first
        all_relevant_txs = all_relevant_txs + address_txs['txs']

    data_before_issuance = []
    data_after_issuance = []
    found_issuance = False
    for tx in all_relevant_txs:
        # tx hash needs to be identical with txid from proof and that is the
        # actual issuance
        if tx['hash'] == txid:
            found_issuance = True

        outs = tx['outputs']
        for o in outs:
            # get op_return_hex, if any, and exit
            if o['script'].startswith('6a'):
                script = o['script']
                # when > 75 op_pushdata1 (4c) is used before length
                if script.startswith('6a4c'):
                    # 2 for 1 byte op_return + 2 for 1 byte op_pushdata1 + 2 for 1 byte data length
                    ignore_hex_chars = 6
                else:
                    # 2 for 1 byte op_return + 2 for 1 byte data length
                    ignore_hex_chars = 4

                if not found_issuance:
                    # to check certs revocations we can iterate this list in reverse!
                    data_after_issuance.append(script[ignore_hex_chars:])
                else:
                    # current issuance is actually the first element of this list!
                    # to check for addr revocations we can iterate this list as is
                    data_before_issuance.append(script[ignore_hex_chars:])

    if not found_issuance:
        raise ValueError("Txid for issuance not found in address' transactions")

    return data_before_issuance, data_after_issuance


#def get_op_return_hex_from_blockchain(txid, testnet=False):
#    # uses blockcypher API for now -- TODO: expand to consult multiple services
#    if testnet:
#        blockcypher_url = "https://api.blockcypher.com/v1/btc/test3/txs/" + txid
#    else:
#        blockcypher_url = "https://api.blockcypher.com/v1/btc/main/txs/" + txid
#
#    response = requests.get(blockcypher_url).json()
#    outputs = response['outputs']
#    hash_hex = ""
#    for o in outputs:
#        script = o['script']
#        if script.startswith('6a'):
#            # when > 75 op_pushdata1 (4c) is used before length
#            if script.startswith('6a4c'):
#                # 2 for 1 byte op_return + 2 for 1 byte op_pushdata1 + 2 for 1 byte data length
#                ignore_hex_chars = 6
#            else:
#                # 2 for 1 byte op_return + 2 for 1 byte data length
#                ignore_hex_chars = 4
#
#            hash_hex = script[ignore_hex_chars:]
#            break
#    return hash_hex


