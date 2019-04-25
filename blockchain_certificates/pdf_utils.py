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


'''
Adds metadata only with values from a CSV file to ready-made PDF certificates.
Expects certificates_directory with all the PDF certificates. The names of the
certificates must begin with the column chosen in cert_names_csv_column.
'''
def add_metadata_only_to_pdf_certificates(conf, interactive=False):
    graduates_csv_file = os.path.join(conf.working_directory, conf.graduates_csv_file)
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    if interactive:
        print('\nConfigured values are:\n')
        print('working_directory:\t{}'.format(conf.working_directory))
        print('graduates_csv_file:\t{}'.format(graduates_csv_file))
        print('certificates_directory:\t{}'.format(certificates_directory))
        print('cert_names_csv_column:\t{}'.format(conf.cert_names_csv_column))
        print('issuer:\t\t\t{}'.format(conf.issuer))
        print('issuer_address:\t\t{}'.format(conf.issuing_address))
        print('cert_metadata_columns:\t{}'.format(conf.cert_metadata_columns))
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

    data = _process_csv(graduates_csv_file, conf.certificates_global_fields)
    for cert_data in data:
        certificate_file = None
        # get student_id to use to get the appropriate certificate
        student_id = cert_data[conf.cert_names_csv_column]
        # find PDF file that starts with student_id
        for fp in cert_files:
            filename = os.path.basename(fp)
            if os.path.isfile(fp) and filename.startswith(student_id):
                certificate_file = fp
                break

        if certificate_file:
            _fill_pdf_metadata(certificate_file, conf.issuer, conf.issuing_address,
                               conf.cert_metadata_columns, cert_data,
                               interactive)
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
    graduates_csv_file = os.path.join(conf.working_directory, conf.graduates_csv_file)
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    if interactive:
        print('\nConfigured values are:\n')
        print('working_directory:\t{}'.format(conf.working_directory))
        print('pdf_cert_template_file:\t{}'.format(pdf_cert_template_file))
        print('graduates_csv_file:\t{}'.format(graduates_csv_file))
        print('certificates_directory:\t{}'.format(certificates_directory))
        print('cert_names_csv_column:\t{}'.format(conf.cert_names_csv_column))
        print('issuer:\t\t\t{}'.format(conf.issuer))
        print('issuer_address:\t\t{}'.format(conf.issuing_address))
        print('cert_metadata_columns:\t{}'.format(conf.cert_metadata_columns))
        consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
        if not consent:
            sys.exit()

    # create certs_dir if it does not exist
    os.makedirs(certificates_directory, exist_ok=True)

    data = _process_csv(graduates_csv_file, conf.certificates_global_fields)
    for cert_data in data:
        # get name to use for cert name
        fullname = cert_data[conf.cert_names_csv_column].replace(' ', '_')
        out_file = os.path.join(certificates_directory, fullname + ".pdf")

        _fill_pdf_form(cert_data, pdf_cert_template_file, out_file)

        _fill_pdf_metadata(out_file, conf.issuer, conf.issuing_address,
                           conf.cert_metadata_columns, cert_data, interactive)


def _process_csv(csv_file, global_fields_str):
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
        # get global fields from json string and add to current field list
        global_fields_json = json.loads(global_fields_str)
        for k, v in global_fields_json.items():
            field[k] = v
        data.append(field)
    return data


'''
Fills in the pdf form using java code that uses the itextpdf java library. This
library is much better than the one used in pdftk (python alternative) and more
importantly it properly supports UTF-8 characters.
'''
def _fill_pdf_form(fields, pdf_cert_template_file, out_file):

    # prepare arguements for java
    fields_json_string = json.dumps(fields).replace('"', '\\"')
    real_path = os.path.dirname(os.path.realpath(__file__))
    java_path = real_path + os.path.sep + "java"

    # TODO: it is inefficient to start the JVM for every certificate
    # TODO: cmd too long, cleanup
    cmd = 'java -cp {java_path}{pathsep}{java_path}{sep}itextpdf-5.5.10.jar{pathsep}{java_path}{sep}json-simple-1.1.1.jar FillPdf "{pdf_cert_template_file}" "{out_file}" "{fields_json_string}"'.format(java_path=java_path, pathsep=os.path.pathsep, sep=os.path.sep, pdf_cert_template_file=pdf_cert_template_file, out_file=out_file, fields_json_string=fields_json_string)
    os.system(cmd)



'''
Inserts standard metadata to a pdf certfificate. All CSV fields in 'data'
are added as metadata to the JSON metadata_object. It then adds the
required 'issuer' and 'issuer_address' as well as an empty
chainpoint_proof key.
'''
def _fill_pdf_metadata(out_file, issuer, issuer_address, columns, data,
                       interactive=False):
    # create metadata objest (json)
    metadata_object = {}
    metadata_fields = columns.split(",")
    for md in metadata_fields:
        if md in data:
            metadata_object[md] = data[md]

    # issuer and issuer_address used to go as separate metadata fields
    # but now go to the metadata_object. They are still compulsory!
    # The validator that reads metadata requires to look for issuer and
    # issuer_address both in the metadata_object and if not found it has
    # to look for them as separate metadata fields for backwards
    # compatibility (certificates issued with v0.9.3 and before)
    metadata_object['issuer'] = issuer
    metadata_object['issuer_address'] = issuer_address

    # add the metadata
    metadata = PdfDict(metadata_object=json.dumps(metadata_object),
                       chainpoint_proof='')
    pdf = PdfReader(out_file)
    pdf.Info.update(metadata)
    PdfWriter().write(out_file, pdf)

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

