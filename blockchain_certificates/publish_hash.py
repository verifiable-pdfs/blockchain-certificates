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

from bitcoinutils.setup import setup
from bitcoinutils.proxy import NodeProxy
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import P2pkhAddress
from bitcoinutils.script import Script


'''
Issues bytes to the Bitcoin's blockchain using OP_RETURN.
'''
def issue_op_return(conf, op_return_bstring, interactive=False):

    op_return_hex = binascii.hexlify(op_return_bstring).decode()

    if interactive:
        print('\nConfigured values are:\n')
        print('working_directory:\t{}'.format(conf.working_directory))
        print('issuing_address:\t{}'.format(conf.issuing_address))
        print('full_node_url:\t\t{}'.format(conf.full_node_url))
        print('full_node_rpc_user:\t{}'.format(conf.full_node_rpc_user))
        print('testnet:\t\t{}'.format(conf.testnet))
        print('tx_fee_per_byte:\t{}'.format(conf.tx_fee_per_byte))
        print('Bytes for OP_RETURN:\n{}'.format(op_return_bstring))
        print('Hex for OP_RETURN:\n{}'.format(op_return_hex))

    op_return_cert_protocol = op_return_hex

    if interactive:
        consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
        if not consent:
            sys.exit()

    # test explicitly when non interactive
    if interactive:
        conf.full_node_rpc_password = getpass.getpass('\nPlease enter the password for the node\'s RPC user: ')

    # initialize full node connection
    if(conf.testnet):
        setup('testnet')
    else:
        setup('mainnet')

    host, port = conf.full_node_url.split(':')   # TODO: update when NodeProxy accepts full url!
    proxy = NodeProxy(conf.full_node_rpc_user, conf.full_node_rpc_password,
                      host, port).get_proxy()

    # create transaction
    tx_outputs = []
    unspent = sorted(proxy.listunspent(1, 9999999, [conf.issuing_address]),
                     key=lambda x: hash(x['amount']), reverse=True)

    issuing_pubkey = proxy.getaddressinfo(conf.issuing_address)['pubkey']

    tx_inputs = [ TxInput(unspent[0]['txid'], unspent[0]['vout']) ]
    input_amount = unspent[0]['amount']

    change_script_out = P2pkhAddress(conf.issuing_address).to_script_pub_key()
    change_output = TxOutput(input_amount, change_script_out)

    op_return_output = TxOutput(0, Script(['OP_RETURN', op_return_cert_protocol]))
    tx_outputs = [ change_output, op_return_output ]

    tx = Transaction(tx_inputs, tx_outputs)

    # sign transaction to get its size
    r = proxy.signrawtransactionwithwallet(tx.serialize())
    if r['complete'] == None:
        if interactive:
            sys.exit("Transaction couldn't be signed by node")
        else:
            raise RuntimeError("Transaction couldn't be signed by node")

    signed_tx = r['hex']
    signed_tx_size = len(signed_tx)

    # calculate fees and change
    tx_fee = (signed_tx_size // 2 + 1) * conf.tx_fee_per_byte

    # note results is sometimes in e- notation
    change_amount = input_amount - (tx_fee / 100000000)

    if(change_amount < 0):
        if interactive:
            sys.exit("Specified address cannot cover the transaction fee of: {} satoshis".format(tx_fee))
        else:
            raise RuntimeError("insufficient satoshis, cannot create transaction")

    # update tx out for change and re-sign
    tx.outputs[0].amount = change_amount
    r = proxy.signrawtransactionwithwallet(tx.serialize())
    if r['complete'] == None:
        if interactive:
            sys.exit("Transaction couldn't be signed by node")
        else:
            raise RuntimeError("Transaction couldn't be signed by node")
    signed_tx = r['hex']

    # send transaction
    if interactive:
        print('The fee will be {} satoshis.\n'.format(tx_fee))
        consent = input('Do you want to issue on the blockchain? [y/N]: ').lower() in ('y', 'yes')
        if not consent:
            sys.exit()

    tx_id = proxy.sendrawtransaction(signed_tx)
    return tx_id



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
    p.add_argument('-a', '--issuing_address', type=str, help='the issuing address with enough funds for the transaction; assumed to be imported in local node wallet')
    p.add_argument('-n', '--full_node_url', type=str, default='127.0.0.1:18332', help='the url of the full node to use')
    p.add_argument('-u', '--full_node_rpc_user', type=str, help='the rpc user as specified in the node\'s configuration')
    p.add_argument('-t', '--testnet', action='store_true', help='specify if testnet or mainnet will be used')
    p.add_argument('-f', '--tx_fee_per_byte', type=int, default=100, help='the fee per transaction byte in satoshis')
    args, _ = p.parse_known_args()
    return args

# used primarily for testing
def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()

    # test with metadata and fake root
    txid = issue_op_return(conf, "3132333435363738393031323334353637383930313233343536373839303132333435363738393031323334353637383930313233343536373839303132333435363738393031323334353637383930", True)

    print('Transaction was sent to the network. The transaction id is:\n{}'.format(txid))


if __name__ == "__main__":
    main()
