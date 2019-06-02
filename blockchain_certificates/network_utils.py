'''
Functions related to network services
'''
import requests
from threading import Thread


'''
Gets all the op_return hexes stored from the specified txid (used to issue the
certificates. Get tx before issuance (for checking revoked addresses) and after
issuance (for checking revoked batches and/or certificates
'''
def get_all_op_return_hexes(address, txid, testnet=False):

    # hard-coded services for now
    services = ['blockcypher', 'blockcypher2']
    required_successes = 1
    successes = 0
    threads_results = {s:{'success':False, 'before':[], 'after':[]} for s in services}
    final_results = []

    # threads to call all functions/APIs simultaneously
    threads = []
    for s in services:
        target = globals()["get_" + s + "_op_return_hexes"]
        thread = Thread(target=target, args=[address, txid, threads_results, s, testnet])
        thread.start()
        threads.append(thread)

    # execute threads
    for t in threads:
        t.join()

    # logic that makes sure that there is enough decentralization and
    # redundancy in the results; currently ensure that we have
    # required_successes identical results returned from all the services
    for s in services:
        if threads_results[s]['success']:
            successes += 1
            final_results.append(threads_results[s])
            if successes >= required_successes:
                break

    if successes >= required_successes:
        if len(final_results) > 1:
            for i in range(1, len(final_results)):
                if final_results[0] != final_results[i]:
                    raise ValueError("API services produced different results")
        return final_results[0]['before'], final_results[0]['after']
    else:
        raise ValueError("Not enough API services results")



'''USED AS A 2ND TEST SERVICE'''
def get_blockcypher2_op_return_hexes(address, txid, results, key, testnet=False):
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
                data = get_op_return_data_from_script(o['script'])

                if not found_issuance:
                    # to check certs revocations we can iterate this list in reverse!
                    data_after_issuance.append(data)
                else:
                    # current issuance is actually the first element of this list!
                    # to check for addr revocations we can iterate this list as is
                    data_before_issuance.append(data)

    if not found_issuance:
        raise ValueError("Txid for issuance not found in address' transactions")

    results[key]['before'] = data_before_issuance
    results[key]['after'] = data_after_issuance
    results[key]['success'] = True



def get_blockcypher_op_return_hexes(address, txid, results, key, testnet=False):
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
                data = get_op_return_data_from_script(o['script'])

                if not found_issuance:
                    # to check certs revocations we can iterate this list in reverse!
                    data_after_issuance.append(data)
                else:
                    # current issuance is actually the first element of this list!
                    # to check for addr revocations we can iterate this list as is
                    data_before_issuance.append(data)

    if not found_issuance:
        raise ValueError("Txid for issuance not found in address' transactions")

    results[key]['before'] = data_before_issuance
    results[key]['after'] = data_after_issuance
    results[key]['success'] = True


def get_bitcoincore_op_return_hexes(address, txid, results, key,
                                    testnet=False):
    pass


def get_op_return_data_from_script(script):
    # when > 75 op_pushdata1 (4c) is used before length
    if script.startswith('6a4c'):
        # 2 for 1 byte op_return + 2 for 1 byte op_pushdata1 + 2 for 1 byte
        # data length
        ignore_hex_chars = 6
    else:
        # 2 for 1 byte op_return + 2 for 1 byte data length
        ignore_hex_chars = 4

    return script[ignore_hex_chars:]

