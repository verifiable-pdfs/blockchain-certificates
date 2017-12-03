'''
Functions related to network services
'''
import requests


'''
Gets all the op_return hexes stored from the specified txid (used to issue the
certificates. Get tx before issuance (for checking revoked addresses) and after
issuance (for checking revoked batches and/or certificates
'''
def get_all_op_return_hexes(txid, testnet=False):
    blockcypher_url = 'http://api.blockcypher.com/v1/btc'
    network = 'test3' if testnet else 'main'

    tx_url = '{}/{}/txs/{}'.format(blockcypher_url, network, txid)
    tx = requests.get(tx_url).json()
    issuance_block_height = tx['block_height']
    address = tx['inputs'][0]['addresses'][0]

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
    for tx in all_relevant_txs:
        current_height = tx['block_height']
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

                if current_height > issuance_block_height:
                    data_after_issuance.append(script[ignore_hex_chars:])
                else:
                    # note that if on the same block it goes to the before
                    # group. That is because we want a revoke address on the
                    # same block as the issuance to invalidate the issuance
                    data_before_issuance.append(script[ignore_hex_chars:])


    return data_before_issuance, data_after_issuance

