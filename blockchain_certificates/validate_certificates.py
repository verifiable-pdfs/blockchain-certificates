'''
Validates a chain point v2 pdf certificate. It acquires the chainpoint_proof from the pdf's metadata, copies the certificate and removes chainpoint_proof to get the original certificate's hash
'''
import os
import sys
import json
import shutil
import hashlib
import configargparse
from pdfrw import PdfReader, PdfWriter, PdfDict
from blockchain_certificates import cred_protocol
from blockchain_certificates import network_utils
from blockchain_certificates import utils
from blockchain_proofs import ChainPointV2

'''
Reads the chainpoint_proof metadata from the pdf file and then removes it
'''
def get_and_remove_chainpoint_proof(pdf_file):
    pdf = PdfReader(pdf_file)
    try:
        proof = json.loads( pdf.Info.chainpoint_proof.decode() )
    except AttributeError:
        return None
    metadata = PdfDict(chainpoint_proof='')
    pdf.Info.update(metadata)
    PdfWriter().write(pdf_file, pdf)
    return proof

'''
Validate the certificate
'''
def validate_certificate(cert, issuer_identifier, testnet):
    filename = os.path.basename(cert)
    tmp_filename =  '__' + filename
    shutil.copy(cert, tmp_filename)

    proof = get_and_remove_chainpoint_proof(tmp_filename)
    if proof == None:
        os.remove(tmp_filename)
        return False, "no chainpoint_proof in metadata"

    # get the hash after removing the metadata
    filehash = ''
    with open(tmp_filename, 'rb') as pdf_file:
        filehash = hashlib.sha256(pdf_file.read()).hexdigest()

    # cleanup now that we got original filehash
    os.remove(tmp_filename)

    # validate receipt
    cp = ChainPointV2()
    if not cp.validate_receipt(proof, filehash, issuer_identifier, testnet):
        return False, "hash and chainpoint_proof did not produce the expected merkle root"

    # blockchain receipt is valid but we need to also check if the certificate
    # was revoked after issuing
    txid = proof['anchors'][0]['sourceId']
    data_before_issuance, data_after_issuance = network_utils.get_all_op_return_hexes(txid, testnet)

    # check if cert or batch was revoked from oldest to newest; if a valid
    # revoke address is found further commands are ignored
    # (TODO: REVOKE ADDRESS CMD
    for op_return in reversed(data_after_issuance):
        cred_dict = cred_protocol.parse_op_return_hex(op_return)
        if cred_dict:
            if cred_dict['cmd'] == cred_protocol.hex_op('op_revoke_batch'):
                if txid == cred_dict['data']['txid']:
                    return False, "batch was revoked"
            elif cred_dict['cmd'] == cred_protocol.hex_op('op_revoke_creds'):
                if txid == cred_dict['data']['txid']:
                    # compare the certificate hash bytes
                    filehash_bytes = utils.hex_to_bytes(filehash)
                    ripemd_filehash = utils.ripemd160(filehash_bytes)
                    ripemd_hex = utils.bytes_to_hex(ripemd_filehash)
                    if ripemd_hex == cred_dict['data']['hashes'][0]:
                        return False, "cert hash was revoked"

                    if len(cred_dict['data']['hashes']) > 1:
                        if ripemd_hex == cred_dict['data']['hashes'][1]:
                            return False, "cert hash was revoked"
            elif cred_dict['cmd'] == cred_protocol.hex_op('op_revoke_address'):
                # if correct address and valid revoke then stop checking other
                # revokes and break loop (TODO: REVOKE ADDRESS CMD)
                if interactive:
                    print("TODO: revoke address not implemented yet!")
                else:
                    raise NotImplementedError("revoke address is not implemented")

    # check if cert's issuance is after a revoke address cmd on that address
    # TODO: REVOKE ADDRESS CMD
    # check the data_before_issuance...  and return False!!

    return True, None



'''
Loads and returns the configuration options (either from --config or from
specifying the specific options.
'''
def load_config():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    default_config = os.path.join(base_dir, 'config.ini')
    p = configargparse.getArgumentParser(default_config_files=[default_config])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('-t', '--testnet', action='store_true', help='specify if testnet or mainnet will be used')
    p.add_argument('-p', '--issuer_identifier', type=str, help='optional 8 bytes issuer code to be displayed in the blockchain')
    p.add_argument('-f', nargs='+', help='a list of certificate pdf files to validate')
    args, _ = p.parse_known_args()
    return args


def validate_certificates(conf, interactive=False):
    if len( conf.f ) >= 1:
        certificates = conf.f
        for cert in certificates:
            results_array = []
            if os.path.isfile(cert):
                filename = os.path.basename(cert)
                if(filename.lower().endswith('.pdf')):
                    valid, reason = validate_certificate(cert,
                                                         conf.issuer_identifier,
                                                         conf.testnet)
                    if valid:
                        if interactive:
                            print('Certificate {} is valid!'.format(cert))
                        else:
                            results_array.append({ "cert": cert, "status": "valid" })
                    else:
                        if interactive:
                            print('Certificate {} is _not_ valid!'.format(cert))
                        else:
                            results_array.append({ "cert": cert, "status":
                                                  "invalid", "reason": reason })
                else:
                    if interactive:
                        print('Skipping non-pdf file: {}'.format(cert))
                    else:
                        results_array.append({ "cert": cert, "status": "N/A",
                                              "reason": "not a pdf file" })
            else:
                if interactive:
                    print('Skipping non-existent file {}'.format(cert))
                else:
                    results_array.append({ "cert": cert, "status": "N/A",
                                          "reason": "file not found" })

            return { "results": results_array } 
    else:
        if interactive:
            exit('At least one certificate needs to be provided as an argument.')
        else:
            raise ValueError("no certificates provided")



def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()
    validate_certificates(conf, interactive=True)


if __name__ == "__main__":
    main()
