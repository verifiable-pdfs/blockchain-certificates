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
from blockchain_certificates.chainpoint import ChainPointV2

'''
Gets issuer address from pdf metadata; requires backward compatibility using
vpdf metadata version
'''
def get_issuer_address_and_proof(pdf_file):
    pdf = PdfReader(pdf_file)
    try:
        version = pdf.Info.version
        proof = json.loads( pdf.Info.chainpoint_proof.decode() )
        if(version == '1' or version == '2'):
            issuer = json.loads( pdf.Info.issuer.decode() )
            return issuer['identity']['address'], proof
        else:           # older versions for backwards compatibility
            issuer_address = pdf.Info.issuer_address
            if issuer_address:
                return issuer_address.decode(), proof
            else:
                metadata_object = json.loads( pdf.Info.metadata_object.decode() )
                return metadata_object['issuer_address'], proof
    except AttributeError:
        raise ValueError("Could not find issuer address or chainpoint proof in pdf")



'''
Gets issuer verification methods from pdf metadata; only available from pdf
vpdf version 1 onwards
'''
def get_issuer_verification(pdf_file):
    pdf = PdfReader(pdf_file)
    try:
        version = pdf.Info.version
        if(version == '1' or version == '2'):
            issuer = json.loads( pdf.Info.issuer.decode() )
            return issuer['identity']['verification']
    except AttributeError:
        raise ValueError("Could not find issuer address verification in pdf")



#'''
#Gets vpdf version
#'''
#def get_version(pdf_file):
#    pdf = PdfReader(pdf_file)
#    try:
#        return pdf.Info.version
#    except AttributeError:
#        raise ValueError("Could not find version metadata in pdf")



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
Returns owner and owner_proof metadata from the pdf file and then removes it
vpdf version 2 onwards
'''
def get_owner_and_remove_owner_proof(pdf_file):
    pdf = PdfReader(pdf_file)
    try:
        version = pdf.Info.version
        if(version == '2'):
            owner = pdf.Info.owner.decode()
            proof = pdf.Info.owner_proof.decode()
        else:
            return None, None
    except AttributeError:
        return None, None
    metadata = PdfDict(owner_proof='')
    pdf.Info.update(metadata)
    PdfWriter().write(pdf_file, pdf)
    if proof:
        owner = json.loads(owner)

    return owner, proof


'''
Get the blockchain network and whether it is testnet plus the txid
Before v2.1.0 only bitcoin was supported and thus BTCOpReturn. Thus for
backward compatibility we also pass the address to help us determine if it is
testnet or not.
'''
def get_chain_testnet_txid_from_chainpoint_proof(proof, address):

    # current only a single anchor is alloed at a time; thus 0
    chain_type = proof['anchors'][0]['type']
    txid = proof['anchors'][0]['sourceId']

    if(chain_type == 'BTCOpReturn'):
        # only for certs issued before v2.1.0 override testnet according to the
        # address used (only bitcoin and BTCOpReturn was used back then)
        if(address.startswith('m') or address.startswith('n') or
           address.startswith('tb1')):
           return 'bitcoin', True, txid

        return 'bitcoin', False, txid
    elif(chain_type == 'LTCOpReturn'):
        return 'litecoin', False, txid
    elif(chain_type == 'BTCTestnetOpReturn'):
        return 'bitcoin', True, txid
    elif(chain_type == 'LTCTestnetOpReturn'):
        return 'litecoin', True, txid



'''
Validate the certificate
Version 2.1.0 has BtcOpReturn, LtcOpReturn, BtcTestnetOpReturn and LtcTestnetOpReturn
Versions <2.1.0 depend on testnet parameter to be set (it only supported
BtcOpReturn)!
'''
def validate_certificate(cert, issuer_identifier, blockchain_services):
    filename = os.path.basename(cert)
    tmp_filename =  '__' + filename
    shutil.copy(cert, tmp_filename)

    # returned proof can be ignored here but could compare with proof later on
    issuer_address, _ = get_issuer_address_and_proof(tmp_filename)

    proof = get_and_remove_chainpoint_proof(tmp_filename)
    if proof == None:
        return False, "no chainpoint_proof in metadata"

    # get the hash after removing the metadata
    filehash = ''
    with open(tmp_filename, 'rb') as pdf_file:
        filehash = hashlib.sha256(pdf_file.read()).hexdigest()

    # instantiate chainpoint object
    cp = ChainPointV2()

    chain, testnet, txid = get_chain_testnet_txid_from_chainpoint_proof(proof,
                                                                        issuer_address)

    # make request to get txs regarding this address
    # issuance is the first element of data_before_issuance
    data_before_issuance, data_after_issuance = \
        network_utils.get_all_op_return_hexes(issuer_address, txid,
                                              blockchain_services, chain,
                                              testnet)

    # validate receipt
    valid, reason = cp.validate_receipt(proof, data_before_issuance[0], filehash, issuer_identifier)

    # display error except when the certificate expired; this is because we want
    # revoked certificate error to be displayed before cert expired error
    # TODO clean hard-coded reason
    if not valid and not reason.startswith("certificate expired"):
        return False, reason

    # load apropriate blockchain libraries
    if(chain == 'litecoin'):
        from litecoinutils.setup import setup
        from litecoinutils.keys import P2pkhAddress, P2wpkhAddress, PublicKey
        from litecoinutils.utils import is_address_bech32
    else:
        from bitcoinutils.setup import setup
        from bitcoinutils.keys import P2pkhAddress, P2wpkhAddress, PublicKey
        from litecoinutils.utils import is_address_bech32

    # set appropriate network (required for addr->pkh in revoke address)
    if testnet:
        setup('testnet')
    else:
        setup('mainnet')


    # check if cert's issuance is after a revoke address cmd on that address
    # and if yes then the issuance is invalid (address was revoked)
    # we check before checking for cert revocations since if the issuance was
    # after an address revocation it should show that as an invalid reason
    # 0 index is the actual issuance -- ignore it
    for i in range( len(data_before_issuance) )[1:] :
        cred_dict = cred_protocol.parse_op_return_hex(data_before_issuance[i])
        if cred_dict:
            if cred_dict['cmd'] == cred_protocol.hex_op('op_revoke_address'):
                if(is_address_bech32(issuer_address)):
                    issuer_pkh = P2wpkhAddress(issuer_address).to_hash160()
                else:
                    issuer_pkh = P2pkhAddress(issuer_address).to_hash160()
                if issuer_pkh == cred_dict['data']['pkh']:
                    return False, "address was revoked"


    # check if cert or batch was revoked from oldest to newest
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
                # if address revocation is found stop looking since all other
                # revocations will be invalid
                if(is_address_bech32(issuer_address)):
                    issuer_pkh = P2wpkhAddress(issuer_address).to_hash160()
                else:
                    issuer_pkh = P2pkhAddress(issuer_address).to_hash160()
                if issuer_pkh == cred_dict['data']['pkh']:
                    break

    # if not revoked but not valid this means that it was expired; now that we
    # checked for revocations we can show the expiry error
    if not valid:
        return False, reason

    # now that the issuer (anchoring) was validated validate the certificate
    # with the owner's public key (vpdf v2)

    # get owner and owner_proof removing the latter
    owner, owner_proof = get_owner_and_remove_owner_proof(tmp_filename)
    if owner:
        # get public key
        pk = PublicKey.from_hex(owner['pk'])
        # get file hash
        sha256_hash = None
        with open(tmp_filename, 'rb' ) as pdf:
            sha256_hash = hashlib.sha256(pdf.read()).hexdigest()

        # finally check if owner signature is valid
        #print(pk.get_address().to_string(), pk.to_hex(), sha256_hash, owner_proof)
        try:
            if( pk.verify(owner_proof, sha256_hash) ):
                pass
        except Exception:   #BadSignatureError:
            return False, 'owner signature could not be validated'
        finally:
            # cleanup
            os.remove(tmp_filename)
    else:
        # cleanup now that we know it validated
        os.remove(tmp_filename)

    # in a valid credential the reason could contain an expiry date
    return True, reason



'''
Loads and returns the configuration options (either from --config or from
specifying the specific options.
'''
def load_config():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    default_config = os.path.join(base_dir, 'config.ini')
    p = configargparse.getArgumentParser(default_config_files=[default_config])
    p.add_argument('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('-l', '--blockchain', type=str, default='bitcoin', 
                   help='choose blockchain; currently bitcoin or litecoin')
    p.add_argument('-t', '--testnet', action='store_true', help='specify if testnet or mainnet will be used')
    p.add_argument('-u', '--full_node_rpc_user', type=str, help='the rpc user as specified in the node\'s configuration')
    p.add_argument('-w', '--full_node_rpc_password', type=str, help='the rpc password as specified in the node\'s configuration')
    p.add_argument('-p', '--issuer_identifier', type=str, help='optional 8 bytes issuer code to be displayed in the blockchain')
    p.add_argument('-b', '--blockchain_services', type=str,
                   default='{ "services": [ {"blockcypher":{} } ], "required_successes": 1}',
                   help='Which blockchain services to use and the minimum required successes')
    p.add_argument('-f', nargs='+', help='a list of certificate pdf files to validate')
    args, _ = p.parse_known_args()
    return args


def validate_certificates(conf, interactive=False):
    if len( conf.f ) >= 1:
        certificates = conf.f
        results_array = []
        for cert in certificates:
            if os.path.isfile(cert):
                filename = os.path.basename(cert)
                if(filename.lower().endswith('.pdf')):
                    valid, reason = validate_certificate(cert,
                                                         conf.issuer_identifier,
                                                         json.loads(conf.blockchain_services))
                    if valid:
                        # get issuer and chainpoint proof
                        issuer_address, proof = get_issuer_address_and_proof(cert)
                        # get blockchain and testnet from proof
                        chain, testnet, _ = get_chain_testnet_txid_from_chainpoint_proof(proof,
                                                                                        issuer_address)
                        # get verification information for issuer
                        verify_issuer = get_issuer_verification(cert)

                        # if valid then check issuer verification methods
                        issuer_verification = None
                        if verify_issuer:
                            issuer_verification = \
                                network_utils.check_issuer_verification_methods(issuer_address,
                                                                                verify_issuer, testnet)
                        if interactive:
                            print('Certificate {} is valid!'.format(cert))
                            if reason:
                                print("(" + reason + ")")
                            if issuer_verification:
                                for k, v in issuer_verification.items():
                                    if k == "domain":
                                        print("Issuer verification method:", k,
                                              "(", v['url'], ")", "->", v['success'])
                                    else:
                                        print("Issuer verification method:", k, "->", v['success'])
                        else:
                            results_array.append({ "cert": cert, "status":
                                                  "valid", "reason": reason,
                                                  "verification": issuer_verification })
                    else:
                        if interactive:
                            print('Certificate {} is _not_ valid!'.format(cert))
                            if reason:
                                print("(" + reason + ")")
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
