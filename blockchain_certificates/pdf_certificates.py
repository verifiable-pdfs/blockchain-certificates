'''
PDF related functions required to populate pdf certificates, hash them and create the index hash document.
'''
import os
import sys
import csv
import json
import glob
import hashlib
from fpdf import FPDF


'''
Populates a pdf form template with values from a CSV file to generate the pdf
certificates.
'''
def populate_pdf_certificates(conf):
    pdf_cert_template_file = os.path.join(conf.working_directory, conf.pdf_cert_template_file)
    graduates_csv_file = os.path.join(conf.working_directory, conf.graduates_csv_file)
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    print('\nConfigured values are:\n')
    print('working_directory:\t{}'.format(conf.working_directory))
    print('pdf_cert_template_file:\t{}'.format(pdf_cert_template_file))
    print('graduates_csv_file:\t{}'.format(graduates_csv_file))
    print('certificates_directory:\t{}'.format(certificates_directory))
    print('cert_names_csv_column:\t{}'.format(conf.cert_names_csv_column))
    consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    data = _process_csv(graduates_csv_file, conf.certificates_global_fields)
    for cert_data in data:
        _fill_pdf_form(cert_data, certificates_directory,
                       pdf_cert_template_file, conf.cert_names_csv_column)

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


"""
Fills in the pdf form using java code that uses the itextpdf java library. This
library is much better than the one used in pdftk (python alternative) and more
importantly it properly supports UTF-8 characters.
"""
def _fill_pdf_form(fields, certs_dir, pdf_cert_template_file, cert_names_csv_column):
    # create certs_dir if it does not exist
    os.makedirs(certs_dir, exist_ok=True)

    # get name to use for cert name
    fullname = fields[cert_names_csv_column]
    out_file = os.path.join(certs_dir, fullname + ".pdf")

    # prepare arguements for java
    fields_json_string = json.dumps(fields).replace('"', '\\"')
    real_path = os.path.dirname(os.path.realpath(__file__))
    java_path = real_path + os.path.sep + "java"

    # TODO: it is inefficient to start the JVM for every certificate
    # TODO: cmd too long, cleanup
    cmd = 'java -cp {java_path}{pathsep}{java_path}{sep}itextpdf-5.5.10.jar{pathsep}{java_path}{sep}json-simple-1.1.1.jar FillPdf "{pdf_cert_template_file}" "{out_file}" "{fields_json_string}"'.format(java_path=java_path, pathsep=os.path.pathsep, sep=os.path.sep, pdf_cert_template_file=pdf_cert_template_file, out_file=out_file, fields_json_string=fields_json_string)
    os.system(cmd)
    # print progress
    print('.', end="", flush=True)


'''
Creates the index pdf file from scratch in order to both use the default
Acroforms _and_ be able to add dynamic text, ie. the hashes
'''
def create_certificates_index(conf, cert_hashes):
    pdf_index_file = os.path.join(conf.working_directory, conf.output_pdf_index_file)
    print('\nIndex file will written in:\n{}\n'.format(pdf_index_file))
    print('Institution name:\n{}\n'.format(conf.institution_name))
    print('Index document title:\n{}\n'.format(conf.index_title))
    print('Index issuing text:\n{}\n'.format(conf.index_issuing_text))
    print('Index validation text:\n{}\n'.format(conf.index_validation_text))
    consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    input_hashes = '\n'.join(cert_hashes)

    pdf = FPDF('L', 'mm', 'A4')
    effective_page_width = pdf.w - 2*pdf.l_margin
    pdf.add_page()

    pdf.set_font('Arial', 'B', 32)
    pdf.cell(effective_page_width, 30, conf.institution_name, 0, 2, 'C')

    pdf.set_font('Arial', 'B', 18)
    pdf.multi_cell(effective_page_width, 7, conf.index_title)
    pdf.ln()

    pdf.set_font('Times', '', 18)
    pdf.multi_cell(effective_page_width, 7, conf.index_issuing_text)
    pdf.ln()

    for t in conf.index_validation_text:
        pdf.set_font('Times', '', 16)
        pdf.multi_cell(effective_page_width, 6, t)
    pdf.ln()

    pdf.add_page()
    pdf.set_font('Times', 'B', 18)
    pdf.cell(effective_page_width, 15, "The certificates' hashes follow:", 0, 2, 'C')

    pdf.set_font('Times', '', 18)
    for h in cert_hashes:
        pdf.cell(effective_page_width, 6, h, 0, 0, 'C')
        pdf.ln()
    pdf.output(pdf_index_file, 'F')



'''
Hashes (sha256) all pdf files found in conf.certificates_directory and returns
them as an array.
'''
def hash_certificates(conf):
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    #print('\nWe will look for .pdf certificates in:\n{}\n'.format(certificates_directory))
    #consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    #if not consent:
    #    sys.exit()

    cert_files = glob.glob(certificates_directory + os.path.sep + "*.pdf")

    hashes = []
    for f in cert_files:
        with open(f, 'rb') as cert:
            hashes.append(hashlib.sha256(cert.read()).hexdigest())

    return hashes


