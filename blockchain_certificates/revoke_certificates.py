'''
Adds a revocation entry to the blockchain. It can revoke specific certificates, a whole batch or future uses of an issuing address.
'''
import os
import sys
import json
import shutil
import hashlib
import binascii
import configargparse
from pdfrw import PdfReader, PdfWriter, PdfDict
from blockchain_certificates import pdf_utils
from blockchain_certificates import publish_hash
from blockchain_certificates import cred_protocol


'''
Creates a tmp file and the certificate without the chainpoint_proof. It gets
the original hash to return and cleans up.
'''
def remove_chainpoint_proof_and_hash(pdf_file):
    filename = os.path.basename(pdf_file)
    tmp_filename =  '__' + filename
    shutil.copy(pdf_file, tmp_filename)

    # get txid and target hash from proof
    pdf = PdfReader(tmp_filename)
    try:
        proof = json.loads( pdf.Info.chainpoint_proof.decode() )
    except AttributeError:
        # TODO: log error
        return None, None
    except json.decoder.JSONDecodeError:
        # TODO: log error
        return None, None

    txid = proof['anchors'][0]['sourceId']
    targetHash = proof['targetHash']

    # remove the proof and get the hash
    metadata = PdfDict(chainpoint_proof='')
    pdf.Info.update(metadata)
    PdfWriter().write(tmp_filename, pdf)

    cert_hash = None
    with open(tmp_filename, 'rb') as cert:
        # note that the cert_hash is a hash object -- can use hexdigest() to debug
        cert_hash = hashlib.sha256(cert.read())
    os.remove(tmp_filename)

    if targetHash == cert_hash.hexdigest():
        return cert_hash.digest(), txid
    else:
        return None, None


'''
Revoke certificates given a list of valid certificates.
'''
def revoke_certificates(conf, interactive=False):
    certificates = conf.p
    # for all certificates remove chainpoint receipt and get original hash
    txid_to_revoke = None
    hashes_to_revoke = []
    for cert in certificates:
        pdf_hash, txid = remove_chainpoint_proof_and_hash(cert)
        if not txid_to_revoke:
            txid_to_revoke = txid
        elif txid_to_revoke != txid:
            if interactive:
                sys.exit("Certificates to revoke are not all part of the same transaction!")
            else:
                raise TypeError("Certificates to revoke are not all part of the same transaction!")

        if pdf_hash:
            hashes_to_revoke.append(pdf_hash)
        else:
            if interactive:
                print('Certificate {} is invalid (possible tampered)! -- Skipping!'.format(cert))
            else:
                # note that if the hash is different from original after
                # removing the chainpoint_proof then fail completely in
                # non-interactive mode
                raise RuntimeError('Certificate {} is invalid (possible tampered)! -- Skipping!'.format(cert))

    # get last certificate if number of certificates is even
    final_odd_hash_to_revoke = None
    if len(hashes_to_revoke) % 2 != 0:
        final_odd_hash_to_revoke = hashes_to_revoke[-1]

    # iterate every two certificates
    revoke_tx_hashes = []
    for hash1, hash2 in zip(hashes_to_revoke[0::2], hashes_to_revoke[1::2]):
        op_return_bstring = cred_protocol.revoke_creds_cmd(txid, hash1, hash2)
        revoked_txid = publish_hash.issue_op_return(conf, op_return_bstring)
        if interactive:
            print('\nTx hash: {}'.format(revoked_txid))
            input('Take a note of the revoke txid and press ENTER to continue...')
        else:
            revoke_tx_hashes.append( { "txid": revoked_txid } )

    if final_odd_hash_to_revoke:
        # issue a final revoke cmd with the last certificate hash
        op_return_bstring = cred_protocol.revoke_creds_cmd(txid, final_odd_hash_to_revoke)
        revoked_txid = publish_hash.issue_op_return(conf, op_return_bstring,
                                                    interactive)
        if interactive:
            print('\nTx hash: {}'.format(revoked_txid))
            input('Take a note of the revoke txid and press ENTER to continue...')
        else:
            revoke_tx_hashes.append( { "txid": revoked_txid } )

    if not interactive:
        return { "results": revoke_tx_hashes }


'''
Revoke a whole certificate batch given a the issuance txid
'''
def revoke_batch(conf, interactive=False):
    txid = conf.batch
    op_return_bstring = cred_protocol.revoke_batch_cmd(txid)
    revoked_txid = publish_hash.issue_op_return(conf, op_return_bstring)
    if interactive:
        print('\nTx hash: {}'.format(revoked_txid))
    else:
        return revoked_txid


'''
Loads and returns the configuration options (either from --config or from
specifying the specific options.
'''
def load_config():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    default_config = os.path.join(base_dir, 'config.ini')
    p = configargparse.getArgumentParser(
            description='Allows to revoke certificates or complete batches or '
                        'even future uses of issuing addresses. All revoked '
                        'certificates need to be part of the same transaction.',
            default_config_files=[default_config])
    p.add('-c', '--config', required=False, is_config_file=True, help='config file path')

    group = p.add_mutually_exclusive_group(required='True')
    group.add_argument('-s', '--address', action='store_true', help='revoke the issuing_address')
    group.add_argument('-b', '--batch', type=str, help='revoke a whole batch identified by its transaction id')
    group.add_argument('-p', nargs='+', help='a list of certificate pdf files to revoke')

    p.add_argument('-d', '--working_directory', type=str, default='.', help='the main working directory - all paths/files are relative to this')
    p.add_argument('-a', '--issuing_address', type=str, help='the issuing address with enough funds for the transaction; assumed to be imported in local node wallet')
    p.add_argument('-n', '--full_node_url', type=str, default='127.0.0.1:18332', help='the url of the full node to use')
    p.add_argument('-u', '--full_node_rpc_user', type=str, help='the rpc user as specified in the node\'s configuration')
    p.add_argument('-t', '--testnet', action='store_true', help='specify if testnet or mainnet will be used')
    p.add_argument('-f', '--tx_fee_per_byte', type=int, default=100, help='the fee per transaction byte in satoshis')
    args, _ = p.parse_known_args()
    return args


def revoke(conf, interactive=False):
    # check if issuance address has not been revoked!
    # TODO: REVOKE ADDRESS CMD

    # check type of revocation and act accordingly
    if(conf.address):
        if interactive:
            print("Address revocation is not implemented yet!")
        else:
            raise NotImplementedError("Address revocation is not implemented yet!")
    elif(conf.batch):
        txid = revoke_batch(conf, interactive)
        return txid
    elif(conf.p):
        txids = revoke_certificates(conf, interactive)
        return txids



def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()
    revoke(conf, True)


if __name__ == "__main__":
    main()
