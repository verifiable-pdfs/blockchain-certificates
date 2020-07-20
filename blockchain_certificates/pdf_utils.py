'''
PDF related functions to create certificates and index.
'''
import os
import sys
import csv
import json
import glob
import hashlib
from pdfrw import PdfReader, PdfWriter, PdfDict
from bitcoinutils.setup import setup
from bitcoinutils.proxy import NodeProxy
from bitcoinutils.keys import PublicKey


'''
Adds metadata only with values from a CSV file to ready-made PDF certificates.
Expects certificates_directory with all the PDF certificates. The names of the
certificates must begin with the column chosen in cert_names_csv_column.
'''
def add_metadata_only_to_pdf_certificates(conf, interactive=False):
    csv_file = os.path.join(conf.working_directory, conf.csv_file)
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    if interactive:
        print('\nConfigured values are:\n')
        print('working_directory:\t{}'.format(conf.working_directory))
        print('csv_file:\t{}'.format(csv_file))
        print('certificates_directory:\t{}'.format(certificates_directory))
        print('cert_names_csv_column:\t{}'.format(conf.cert_names_csv_column))
        print('issuer:\t\t\t{}'.format(conf.issuer))
        print('issuer_address:\t\t{}'.format(conf.issuing_address))
        if conf.verify_issuer:
            print('verify_issuer:\t\t{}'.format(conf.verify_issuer))
        if conf.expiry_date:
            print('expiry_date:\t\t{}'.format(conf.expiry_date))
        if conf.cert_metadata_columns:
            print('cert_metadata_columns:\t{}'.format(conf.cert_metadata_columns))
        if conf.certificates_global_fields:
            print('certificates_global_fields:\t{}'.format(conf.certificates_global_fields))
        consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
        if not consent:
            sys.exit()

    # check if certificates directory exists and exit if not
    if(not os.path.isdir(certificates_directory)):
        if interactive:
            print('Directory {} does not exist.  Exiting.'.format(certificates_directory))
            sys.exit()
        else:
            error_str = "directory {} does not exist".format(certificates_directory)
            raise ValueError(error_str)

    # get a list of all PDF files and exit if none
    cert_files = glob.glob(certificates_directory + os.path.sep + "*.[pP][dD][fF]")
    if not cert_files:
        if interactive:
            print('Directory {} is empty. Exiting.'.format(certificates_directory))
            sys.exit()
        else:
            error_str = "directory {} is empty".format(certificates_directory)
            raise ValueError(error_str)

    data = _process_csv(csv_file) # TODO CLEAN, conf.certificates_global_fields)
    for cert_data in data:
        certificate_file = None
        # get file_id to use to get the appropriate certificate
        file_id = cert_data[conf.cert_names_csv_column]
        # find PDF file that starts with file_id
        for fp in cert_files:
            filename = os.path.basename(fp)
            if os.path.isfile(fp) and filename.startswith(file_id):
                certificate_file = fp
                break

        if certificate_file:
            #import time
            #start = time.time()
            # TODO cleanup - passes full conf anyway to get user/pw for proxy node
            _fill_pdf_metadata(certificate_file, conf.issuer, conf.issuing_address,
                               conf.cert_metadata_columns, cert_data,
                               conf.certificates_global_fields,
                               conf.verify_issuer,
                               conf, interactive)
            #end = time.time()
            #print("_fill_pdf_metadata()", end-start, " seconds")
        else:
            if interactive:
                print('\nSkipping {}\n'.format(certificate_file))
            else:
                # note that in non-interactive if a file is not found we fail
                # completely the issuance
                error_str = "skipping {}".format(certificates_directory)
                raise ValueError(error_str)



'''
Populates a pdf form template with values from a CSV file to generate the pdf
certificates. Also uses the CSV data to add metadata in the pdf file before
hashing.
'''
def populate_pdf_certificates(conf, interactive=False):
    pdf_cert_template_file = os.path.join(conf.working_directory, conf.pdf_cert_template_file)
    csv_file = os.path.join(conf.working_directory, conf.csv_file)
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    if interactive:
        print('\nConfigured values are:\n')
        print('working_directory:\t{}'.format(conf.working_directory))
        print('pdf_cert_template_file:\t{}'.format(pdf_cert_template_file))
        print('csv_file:\t{}'.format(csv_file))
        print('certificates_directory:\t{}'.format(certificates_directory))
        print('cert_names_csv_column:\t{}'.format(conf.cert_names_csv_column))
        print('issuer:\t\t\t{}'.format(conf.issuer))
        print('issuer_address:\t\t{}'.format(conf.issuing_address))
        if conf.verify_issuer:
            print('verify_issuer:\t\t{}'.format(conf.verify_issuer))
        if conf.expiry_date:
            print('expiry_date:\t\t{}'.format(conf.expiry_date))
        if conf.cert_metadata_columns:
            print('cert_metadata_columns:\t{}'.format(conf.cert_metadata_columns))
        if conf.certificates_global_fields:
            print('certificates_global_fields:\t{}'.format(conf.certificates_global_fields))
        consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
        if not consent:
            sys.exit()

    # create certs_dir if it does not exist
    os.makedirs(certificates_directory, exist_ok=True)

    data = _process_csv(csv_file)
    for cert_data in data:
        # get name to use for cert name
        fullname = cert_data[conf.cert_names_csv_column].replace(' ', '_')
        out_file = os.path.join(certificates_directory, fullname + ".pdf")

        _fill_pdf_form(cert_data, pdf_cert_template_file, out_file, interactive)

        # TODO cleanup - passes full conf anyway to get user/pw for proxy node
        _fill_pdf_metadata(out_file, conf.issuer, conf.issuing_address,
                           conf.cert_metadata_columns, cert_data,
                           conf.certificates_global_fields, conf.verify_issuer,
                           conf, interactive)


def _process_csv(csv_file):
    headers = []
    data =  []
    csv_data = csv.reader(open(csv_file))
    for i, row in enumerate(csv_data):
        if i == 0:
            headers = row
            continue;
        field = {}
        # add all csv columns/fields
        for i in range(len(headers)):
            field[headers[i]] = row[i]
        data.append(field)

    return data


'''
Fills in the pdf form using java code that uses the itextpdf java library. This
library is much better than the one used in pdftk (python alternative) and more
importantly it properly supports UTF-8 characters.
'''
def _fill_pdf_form(fields, pdf_cert_template_file, out_file, interactive=False):

    # prepare arguements for java
    fields_json_string = json.dumps(fields).replace('"', '\\"')
    real_path = os.path.dirname(os.path.realpath(__file__))
    java_path = real_path + os.path.sep + "java"

    # TODO: it is inefficient to start the JVM for every certificate
    # TODO: cmd too long, cleanup
    cmd = 'java -cp {java_path}{pathsep}{java_path}{sep}itextpdf-5.5.10.jar{pathsep}{java_path}{sep}json-simple-1.1.1.jar FillPdf "{pdf_cert_template_file}" "{out_file}" "{fields_json_string}"'.format(java_path=java_path, pathsep=os.path.pathsep, sep=os.path.sep, pdf_cert_template_file=pdf_cert_template_file, out_file=out_file, fields_json_string=fields_json_string)
    os.system(cmd)

    if interactive:
        # print progress
        print('+', end="", flush=True)



'''
Inserts standard metadata to a pdf certfificate. All CSV fields in 'data'
and 'global_fields' are added as metadata to the JSON metadata pdf field.
It then adds the required 'version', 'issuer' (name, identity) as well as an empty
chainpoint_proof key.
'''
def _fill_pdf_metadata(out_file, issuer, issuer_address, column_fields, data,
                       global_columns, verify_issuer, conf, interactive=False):

    # create version
    version = 2

    # create issuer object (json)
    issuer = {
        "name": issuer,
        "identity": {
            "address": issuer_address,
            "verification": json.loads(verify_issuer)['methods']
        }
    }

    # create metadata object (json) and add metadata
    metadata = {}

    # add custom metadata
    if column_fields:
        metadata_fields = json.loads(column_fields)['columns']
        for f in metadata_fields:
            key = list(f)[0]
            if key in data:
                field_properties = f[key]
                field_properties['value'] = data[key]
                metadata[key] = field_properties

    # add global field metadata
    if global_columns:
        global_fields = json.loads(global_columns)['fields']
        for g in global_fields:
            key = list(g)[0]
            # note that global fields override column data
            metadata[key] = g[key]

    # now look at special owner name/pubkey columns explicitly in code
    # TODO we should probably check if the public key is valid
    owner = None
    owner_address = None
    owner_pk = None
    if '__OWNER_PK__' in data and data['__OWNER_PK__'] and '__OWNER_ADDRESS__' in data and data['__OWNER_ADDRESS__']:
        # TODO maybe just calculate address from public key?
        owner_address = data['__OWNER_ADDRESS__']
        owner_pk = data['__OWNER_PK__']

        owner = {
            "name": data['__OWNER_NAME__'],
            "owner_address": data['__OWNER_ADDRESS__'], # TODO needed? - can be derived
            "pk": owner_pk
        }

        # add the metadata
        pdf_metadata = PdfDict(version=version, issuer=json.dumps(issuer),
                               metadata=json.dumps(metadata),
                               owner=json.dumps(owner), owner_proof='', chainpoint_proof='')
    else:
        # add the metadata (without dumps(owner) to keep owner empty)
        pdf_metadata = PdfDict(version=version, issuer=json.dumps(issuer),
                               metadata=json.dumps(metadata),
                               owner='', owner_proof='', chainpoint_proof='')


    pdf = PdfReader(out_file)
    if pdf.Info:
        pdf.Info.update(pdf_metadata)
    else:
        pdf.Info = pdf_metadata
    PdfWriter().write(out_file, pdf)

    # if owner exists then need to add owner_proof
    # hash pdf, sign hash message using node and add in owner_proof
    if owner:
        ##import time
        ##start = time.time()
        sha256_hash = None
        with open(out_file, 'rb' ) as pdf:
            sha256_hash = hashlib.sha256(pdf.read()).hexdigest()
        if(conf.testnet):
            setup('testnet')
        else:
            setup('mainnet')

        host, port = conf.full_node_url.split(':') #TODO: update when NodeProxy accepts full url!
        proxy = NodeProxy(conf.full_node_rpc_user, conf.full_node_rpc_password,
                          host, port).get_proxy()

        # Due to an old unresolved issue still pending in Bitcoin v0.20.0
        # signmessage does not support signing with bech32 key.
        # To resolve we use the public key to get the base58check encoding that
        # signmessage is happy with so that we can sign!
        if (owner_address.startswith('bc') or owner_address.startswith('tb')):
            owner_address = PublicKey(owner_pk).get_address().to_string()

        # NOTE that address (the encoding) might have changed here from bech32
        # to legacy... take care if you use it again in this function!

        sig = proxy.signmessage(owner_address, sha256_hash)

        # add owner_proof to metadata
        pdf_metadata = PdfDict(owner_proof=sig)
        pdf = PdfReader(out_file)
        pdf.Info.update(pdf_metadata)
        PdfWriter().write(out_file, pdf)
        ##end = time.time()
        ##print(end-start, " seconds")
        ##exit()

    if interactive:
        # print progress
        print('.', end="", flush=True)



'''
Hashes (sha256) all files passed as an array and returns them as an array.
'''
def hash_certificates(cert_files):
    hashes = []
    for f in cert_files:
        with open(f, 'rb') as cert:
            hashes.append(hashlib.sha256(cert.read()).hexdigest())

    return hashes

