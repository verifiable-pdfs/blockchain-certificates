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
def validate_certificate(cert, hash_prefix, testnet):
    filename = os.path.basename(cert)
    tmp_filename =  '__' + filename
    shutil.copy(cert, tmp_filename)

    proof = get_and_remove_chainpoint_proof(tmp_filename)
    if proof == None:
        os.remove(tmp_filename)
        return False

    # get the hash after removing the metadata
    filehash = ''
    with open(tmp_filename, 'rb') as pdf_file:
        filehash = hashlib.sha256(pdf_file.read()).hexdigest()

    # cleanup now that we got original filehash
    os.remove(tmp_filename)

    # validate receipt
    cp = ChainPointV2()
    if cp.validate_receipt(proof, filehash, hash_prefix, testnet):
        return True
    else:
        return False


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
    p.add_argument('-p', '--hash_prefix', type=str, default='20202020202020', help='prepend the hash that we wish to issue with this hexadecimal')
    p.add_argument('-f', nargs='+', help='a list of certificate pdf files to validate')
    args, _ = p.parse_known_args()
    return args



def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()
    if len( conf.f ) >= 1:
        certificates = conf.f
        for cert in certificates:
            if os.path.isfile(cert):
                filename = os.path.basename(cert)
                if(filename.lower().endswith('.pdf')):
                    if validate_certificate(cert, conf.hash_prefix, conf.testnet):
                        print('Certificate {} is valid!'.format(cert))
                    else:
                        print('Certificate {} is _not_ valid!'.format(cert))
                else:
                    print('Skipping non-pdf file: {}'.format(cert))
            else:
                print('Skipping non-existent file {}'.format(cert))
    else:
        exit('At least one certificate needs to be provided as an argument.')


if __name__ == "__main__":
    main()
