import requests
import binascii
import time
from merkletools import MerkleTools
from blockchain_certificates import cred_protocol
from blockchain_certificates import network_utils
from blockchain_certificates import utils

CHAINPOINT_CONTEXT = 'https://w3id.org/chainpoint/v2'
CHAINPOINT_HASH_TYPES = {'sha224': 'ChainpointSHA224v2',
                         'sha256': 'ChainpointSHA256v2',
                         'sha384': 'ChainpointSHA384v2',
                         'sha512': 'ChainpointSHA512v2',
                         'sha3_224': 'ChainpointSHA3-224v2',
                         'sha3_256': 'ChainpointSHA3-256v2',
                         'sha3_384': 'ChainpointSHA3-384v2',
                         'sha3_512': 'ChainpointSHA3-512v2' }
CHAINPOINT_ANCHOR_TYPES = {'btc': 'BTCOpReturn'} #, 'eth': 'ETHData'}

'''
Implements chainpoint v2 proof of existence approach
'''
class ChainPointV2(object):
    def __init__(self, hash_type="sha256"):
        self.hash_type = hash_type.lower()
        self.mk = MerkleTools(hash_type)

    '''Wraps merkletools method'''
    def reset_tree(self):
        self.mk.reset_tree()

    '''Wraps merkletools method'''
    def add_leaf(self, values, do_hash=False):
        self.mk.add_leaf(values, do_hash)

    '''Wraps merkletools method'''
    def get_leaf(self, index):
        return self.mk.get_leaf(index)

    '''Wraps merkletools method'''
    def get_leaf_count(self):
        return self.mk.get_leaf_count()

    '''Wraps merkletools method'''
    def get_tree_ready_state(self):
        return self.mk.get_tree_ready_state()

    '''Wraps merkletools method'''
    def make_tree(self):
        self.mk.make_tree()

    '''Wraps merkletools method'''
    def get_merkle_root(self):
        return self.mk.get_merkle_root()

    '''Wraps merkletools method'''
    def get_proof(self, index):
        return self.mk.get_proof(index)

    '''Wraps merkletools method'''
    def validate_proof(self, proof, target_hash, merkle_root):
        return self.mk.validate_proof(proof, target_hash, merkle_root)

    def get_chainpoint_hash_type(self):
        return CHAINPOINT_HASH_TYPES[self.hash_type]

    '''
    Returns the chainpoint v2 blockchain receipt for specific leaf
    Currently only works for BTC anchors
    '''
    def get_receipt(self, index, btc_source_id):
        if self.get_tree_ready_state():
            return {
                "@context": CHAINPOINT_CONTEXT,
                "type": self.get_chainpoint_hash_type(),
                "targetHash": self.get_leaf(index),
                "merkleRoot": self.get_merkle_root(),
                "proof": self.get_proof(index),
                "anchors": [
                    {
                        "type": "BTCOpReturn",
                        "sourceId": btc_source_id
                    }
                ]
            }
        else:
            return None


    '''
    Validates a chainpoint receipt. Currently only for BTC anchors
        receipt is the chainpoint_proof metadata from the pdf file.
        certificate_hash is the hash of the certificate after we removed the
            chainpoint_proof metadata
        issuer_identifier is a fixed 8 bytes issuer code that displays on the
            blockchain
        testnet specifies if testnet or mainnet was used
    '''
    # TODO consider using exceptions instead of (bool, text) tuples; this is
    # really only needed for valid but soon to expire
    def validate_receipt(self, receipt, op_return_hex, certificate_hash, issuer_identifier='', testnet=False):
        # check context and hash type
        if(receipt['@context'].lower() != CHAINPOINT_CONTEXT):
            return False, "wrong chainpoint context"
        if(receipt['type'] not in CHAINPOINT_HASH_TYPES.values()):
            return False, "type not in CHAINPOINT_HASH_TYPES"
        target_hash = receipt['targetHash']
        merkle_root = receipt['merkleRoot']
        proof = receipt['proof']

        # validate actual hash
        if target_hash.lower() != certificate_hash.lower():
            return False, "certificate hash is different than the one in receipt"

        # validate merkle proof
        if(not self.validate_proof(proof, target_hash, merkle_root)):
           return False, "certificate's hash is not in merkle root"

        txid = self.get_txid_from_receipt(receipt)

        # validate anchor
        #op_return_hex = network_utils.get_op_return_hex_from_blockchain(txid, testnet)

        # ignore issuer_identifier for now (it is string in CRED but used to be
        # hex so we need a smart way to get it) -- TODO: obsolete it !!!
        #issuer_id_hex = utils.text_to_hex(issuer_identifier)

        # if op_return starts with CRED it is using the meta-protocol
        op_dict = cred_protocol.parse_op_return_hex(op_return_hex)
        if op_dict:
            version_hex = op_dict['version']
            command_hex = op_dict['cmd']
            # could check if it is equal to issuer_id_hex
            issuer_hex = op_dict['data']['issuer_identifier']
            # get merkle root
            hash_hex = op_dict['data']['merkle_root']
            # if issue with expiry get expiry date
            if command_hex == cred_protocol.hex_op('op_issue_abs_expiry'):
                expiry_hex = op_return_hex[96:116]
            else:
                expiry_hex = None
            #print(version_hex)
            #print(command_hex)
            #print(issuer_hex)
            #print(hash_hex)
            #print(merkle_root.lower())
        # otherwise op_return should be fixed to 7 bytes or 14 hex chars (old prefix method)
        else:
            ignore_hex_chars = 14
            hash_hex = op_return_hex[ignore_hex_chars:]

        if(not merkle_root.lower() == hash_hex.lower()):
            return False, "certificate's merkle root is different than the one in the blockchain"

        # only for CRED protocol certificates check expiration date if
        # issued with expiry date
        if op_dict and expiry_hex:
            expiry = utils.hex_to_int(expiry_hex)
            if expiry > int(time.time()):
                return True, "valid until: " + str(expiry)
            else:
                return False, "certificate expired at: " + str(expiry)


        return True, None



    def get_txid_from_receipt(self, receipt):
        # get anchor
        # TODO currently gets only the first valid (BTC) anchor
        anchors = receipt['anchors']
        txid = ''
        for a in anchors:
            if a['type'] in CHAINPOINT_ANCHOR_TYPES.values():
                txid = a['sourceId']
                break
        return txid



def main():
    print("Create tree for values 'a', 'b' and 'c' and display some details about the merkle tree")
    hashes = ['a', 'b', 'c']
    cp = ChainPointV2()
    cp.add_leaf(hashes, True)
    cp.make_tree()
    print("leaf_count: ", cp.get_leaf_count())
    print("root: ", cp.get_merkle_root())
    for x in range(0, len(hashes)):
        print("{}: {}".format(x, cp.get_proof(x)))
        print("\n")

if __name__ == "__main__":
    main()
