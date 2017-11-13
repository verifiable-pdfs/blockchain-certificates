'''
Issues some metadata to Bitcoin's blockchain via OP_RETURN. We currently store
the hash of the index pdf certificate that holds all the hashes for the
certificates.
'''

import os
import sys
import hashlib
import getpass
import binascii
import configargparse

import bitcoin
import bitcoin.rpc
from bitcoin.core import *
from bitcoin.core.script import *
from bitcoin.wallet import *


'''
Issues a hash to the Bitcoin's blockchain using OP_RETURN
'''
def issue_hash(conf, with_metadata, merkle_root):
    print('\nConfigured values are:\n')
    print('working_directory:\t{}'.format(conf.working_directory))
    print('issuing_address:\t{}'.format(conf.issuing_address))
    print('full_node_url:\t\t{}'.format(conf.full_node_url))
    print('full_node_rpc_user:\t{}'.format(conf.full_node_rpc_user))
    print('testnet:\t\t{}'.format(conf.testnet))
    print('tx_fee_per_byte:\t{}'.format(conf.tx_fee_per_byte))
    print('hash_prefix:\t\t{}'.format(conf.hash_prefix))

    hash_hex = ""
    if with_metadata:
        hash_hex = merkle_root
    else:
        pdf_index_file = os.path.join(conf.working_directory, conf.output_pdf_index_file)
        print('pdf_index_file:\t\t{}'.format(pdf_index_file))
        # get index hash from file
        with open(pdf_index_file, 'rb') as index:
            hash_hex = hashlib.sha256(index.read()).hexdigest()

    consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    full_node_rpc_password = getpass.getpass('\nPlease enter the password for the node\'s RPC user: ')


    if(conf.hash_prefix):
        # hash_prefix should be fixed to 7 bytes (14 hex chars)
        fixed_7_char_hex_prefix = binascii.hexlify(_str_to_7_chars(binascii.unhexlify(conf.hash_prefix)))
        blockchain_hash = fixed_7_char_hex_prefix + hash_hex
    else:
        # hash_prefix should be fixed to 7 bytes (14 hex chars)
        # if empty add 7 spaces
        blockchain_hash = '20202020202020' + hash_hex

    # initialize full node connection
    if(conf.testnet):
        bitcoin.SelectParams('testnet')
    else:
        bitcoin.SelectParams('mainnet')

    proxy = bitcoin.rpc.Proxy("http://{0}:{1}@{2}".format(conf.full_node_rpc_user,
                                                          full_node_rpc_password,
                                                          conf.full_node_url))

    # create transaction
    tx_outputs = []
    unspent = sorted(proxy.listunspent(1, 9999999, [conf.issuing_address]),
                     key=lambda x: hash(x['amount']), reverse=True)

    issuing_pubkey = proxy.validateaddress(conf.issuing_address)['pubkey']

    tx_inputs = [ CMutableTxIn(unspent[0]['outpoint']) ]
    input_amount = unspent[0]['amount']

    change_script_out = CBitcoinAddress(conf.issuing_address).to_scriptPubKey()
    change_output = CMutableTxOut(input_amount, change_script_out)

    op_return_output = CMutableTxOut(0, CScript([OP_RETURN, x(blockchain_hash)]))
    tx_outputs = [ change_output, op_return_output ]

    tx = CMutableTransaction(tx_inputs, tx_outputs)

    # sign transaction to get its size
    r = proxy.signrawtransaction(tx)
    assert r['complete']
    signed_tx = r['tx']
    signed_tx_size = len(signed_tx.serialize())

    # calculate fees and change
    tx_fee = signed_tx_size * conf.tx_fee_per_byte
    change_amount = input_amount - tx_fee

    if(change_amount < 0):
        sys.exit("Specified address cannot cover the transaction fee of: {} satoshis".format(tx_fee))

    # update tx out for change and re-sign
    tx.vout[0].nValue = change_amount
    r = proxy.signrawtransaction(tx)
    assert r['complete']
    signed_tx = r['tx']

    # send transaction
    print('The fee will be {} satoshis.\n'.format(tx_fee))
    consent = input('Do you want to issue on the blockchain? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    tx_id = b2lx(proxy.sendrawtransaction(signed_tx))
    return tx_id


'''
Input string is returned as a 7 char string (padding with space if less than 7)
'''
def _str_to_7_chars(string):
    length = len(string)
    if length < 7:
        return string.ljust(7)
    elif length > 7:
        return string[:7]
    else:
        return string


'''
Loads and returns the configuration options (either from --config or from
specifying the specific options).
'''
def load_config():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    default_config = os.path.join(base_dir, 'config.ini')
    p = configargparse.getArgumentParser(default_config_files=[default_config])
    p.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('-d', '--working_directory', type=str, default='.', help='the main working directory - all paths/files are relative to this')
    p.add_argument('-o', '--output_pdf_index_file', type=str, default='index_document.pdf', help='the name of the pdf index document which hash will be stored in the blockchain')
    p.add_argument('-a', '--issuing_address', type=str, help='the issuing address with enough funds for the transaction; assumed to be imported in local node wallet')
    p.add_argument('-n', '--full_node_url', type=str, default='127.0.0.1:18332', help='the url of the full node to use')
    p.add_argument('-u', '--full_node_rpc_user', type=str, help='the rpc user as specified in the node\'s configuration')
    p.add_argument('-t', '--testnet', action='store_true', help='specify if testnet or mainnet will be used')
    p.add_argument('-f', '--tx_fee_per_byte', type=int, default=100, help='the fee per transaction byte in satoshis')
    p.add_argument('-p', '--hash_prefix', type=str, help='prepend the hash that we wish to issue with this hexadecimal')
    args, _ = p.parse_known_args()
    return args

# used primarily for testing
def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()

    # test with metadata and fake root
    txid = issue_hash(conf, True, "38393031323334353637383930313233343536373839303132333435363738393031323334353637383930313233343536373839303132333435363738393031323334353637383930")

    print('Transaction was sent to the network. The transaction id is:\n{}'.format(txid))


if __name__ == "__main__":
    main()
