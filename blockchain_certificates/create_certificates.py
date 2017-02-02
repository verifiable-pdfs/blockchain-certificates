'''
Populates the required pdf form templates: both for individual certificates and for the hash index.
'''
import os
import sys
import csv
import json
import glob
import hashlib
import configargparse
from fpdf import FPDF
#import pypdftk
#from fdfgen import forge_fdf



'''
Populates a pdf form template with values from a CSV file to generate the pdf
certificates.
'''
def populate_pdf_certificates(conf):
    pdf_cert_template_file = os.path.join(conf.working_directory, conf.pdf_cert_template_file)
    pdf_index_template_file = os.path.join(conf.working_directory, conf.pdf_index_template_file)
    graduates_csv_file = os.path.join(conf.working_directory, conf.graduates_csv_file)
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    print('\nConfigured values are:\n')
    print('working_directory:\t{}'.format(conf.working_directory))
    print('pdf_cert_template_file:\t{}'.format(pdf_cert_template_file))
    print('pdf_index_template_file:{}'.format(pdf_index_template_file))
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
    #cmd = 'java -cp {java_path}{pathsep}{java_path}{sep}itext7-kernel-7.0.1.jar{pathsep}{java_path}{sep}itext7-forms-7.0.1.jar{pathsep}{java_path}{sep}itext7-io-7.0.1.jar{pathsep}{java_path}{sep}itext7-layout-7.0.1.jar{pathsep}{java_path}{sep}json-simple-1.1.1.jar{pathsep}{java_path}{sep}slf4j-simple-1.7.22.jar{pathsep}{java_path}{sep}slf4j-api-1.7.22.jar FillPdf "{pdf_cert_template_file}" "{out_file}" "{fields_json_string}"'.format(java_path=java_path, pathsep=os.path.pathsep, sep=os.path.sep, pdf_cert_template_file=pdf_cert_template_file, out_file=out_file, fields_json_string=fields_json_string)
    os.system(cmd)


"""
Fills in the pdf form using the pdftk tool (need to install seperately).
Unfortunately, it does not work for two byte characters, e.g. UTF-8 and thus it
is not used anymore.

OBSOLETE
"""
def _fill_pdf_form_with_pdftk(fields, certs_dir, pdf_cert_template_file, cert_names_csv_column):
    # create certs_dir if it does not exist
    os.makedirs(certs_dir, exist_ok=True)

    # get name to use for cert name
    fullname = fields[cert_names_csv_column]
    tmp_file = os.path.join(certs_dir, fullname + ".fdf")
    out_file = os.path.join(certs_dir, fullname + ".pdf")
    # create tmp fdf file
    fdf = forge_fdf("",fields,[],[],[])
    fdf_file = open(tmp_file, "wb")
    fdf_file.write(fdf)
    fdf_file.close()
    cmd = 'pdftk "{0}" fill_form "{1}" output "{2}" dont_ask flatten'.format(pdf_cert_template_file, tmp_file, out_file)
    os.system(cmd)
    os.remove(tmp_file)

    # warn if name contains any of the problematic utf-8 characters "čČćĆđĐ"
    # actually all chars with ord() > 256 .... 
    problematic_chars = "čČćĆđĐłń"
    if any( (c in problematic_chars) for c in fullname):
       print('Warning: check certificate full name of: {}'.format(fullname))




'''
Uses the hashes array and populates the index template on a multiline field
called 'hashes'. Note that if there are other fields it will try to populate
them using conf.certificates_global_fields

OBSOLETE -- Requires XFA dynamic forms which are not part of the OS PDF
standard!
'''
def populate_certificates_index_with_xfa(conf, cert_hashes):
    pdf_index_template_file = os.path.join(conf.working_directory, conf.pdf_index_template_file)
    final_index_file = os.path.splitext(pdf_index_template_file)[0] + "_final.pdf"
    print('\nWe will use the index_template: {}\n'.format(pdf_index_template_file))
    print('Final index file will written in: {}\n'.format(final_index_file))
    consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    input_hashes = '\n'.join(cert_hashes)

    data = {}
    data['hashes'] = input_hashes

    # get global fields from json string and add to data
    global_fields_json = json.loads(conf.certificates_global_fields)
    for k, v in global_fields_json.items():
        data[k] = v

    # prepare arguements for java
    fields_json_string = json.dumps(data).replace('"', '\\"')
    real_path = os.path.dirname(os.path.realpath(__file__))
    java_path = real_path + os.path.sep + "java"

    # TODO: cmd too long, cleanup
    cmd = 'java -cp {java_path}{pathsep}{java_path}{sep}itextpdf-5.5.10.jar{pathsep}{java_path}{sep}json-simple-1.1.1.jar FillPdf "{pdf_index_template_file}" "{final_index_file}" "{fields_json_string}" xfa'.format(java_path=java_path, pathsep=os.path.pathsep, sep=os.path.sep, pdf_index_template_file=pdf_index_template_file, final_index_file=final_index_file, fields_json_string=fields_json_string)
    print(cmd)
    os.system(cmd)


'''
Uses the hashes array and populates the index template on a multiline field
called 'hashes'. 

OBSOLETE
'''
def populate_certificates_index_with_pdftk(conf, cert_hashes):
    pdf_index_template_file = os.path.join(conf.working_directory, conf.pdf_index_template_file)
    final_index_file = os.path.splitext(pdf_index_template_file)[0] + "_final.pdf"
    print('\nWe will use the index_template: {}\n'.format(pdf_index_template_file))
    print('Final index file will written in: {}\n'.format(final_index_file))
    consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    input_hashes = '\n'.join(cert_hashes)

    # create tmp fdf file
    tmp_file = os.path.splitext(final_index_file)[0] + ".fdf"
    fdf = forge_fdf("",{'hashes': input_hashes},[],[],[])
    fdf_file = open(tmp_file, "wb")
    fdf_file.write(fdf)
    fdf_file.close()
    cmd = 'pdftk "{0}" fill_form "{1}" output "{2}" dont_ask flatten'.format(pdf_index_template_file, tmp_file, final_index_file)
    os.system(cmd)
    os.remove(tmp_file)

'''
Creates the index pdf file from scratch in order to both use the default
Acroforms _and_ be able to add dynamic text, ie. the hashes
'''
def create_certificates_index(conf, cert_hashes):
    pdf_index_template_file = os.path.join(conf.working_directory, conf.pdf_index_template_file)
    final_index_file = os.path.splitext(pdf_index_template_file)[0] + "_final.pdf"
    print('\nWe will use the index_template: {}\n'.format(pdf_index_template_file))
    print('Final index file will written in: {}\n'.format(final_index_file))
    consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    input_hashes = '\n'.join(cert_hashes)
    print("TODO!")



'''
Hashes (sha256) all pdf files found in conf.certificates_directory and returns
them as an array.
'''
def hash_certificates(conf):
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    print('\nWe will look for .pdf certificates in: {}\n'.format(certificates_directory))
    consent = input('Do you want to continue? [y/N]: ').lower() in ('y', 'yes')
    if not consent:
        sys.exit()

    cert_files = glob.glob(certificates_directory + os.path.sep + "*.pdf")

    hashes = []
    for f in cert_files:
        with open(f, 'rb') as cert:
            hashes.append(hashlib.sha256(cert.read()).hexdigest())

    return hashes


'''
Loads and returns the configuration options (either from --config or from
specifying the specific options.
'''
def load_config():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    default_config = os.path.join(base_dir, 'config.ini')
    p = configargparse.getArgumentParser(default_config_files=[default_config])
    p.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('-d', '--working_directory', type=str, default='.', help='the main working directory - all paths/files are relative to this')
    p.add_argument('-p', '--pdf_cert_template_file', type=str, default='cert_template.pdf', help='the pdf certificate form to populate')
    p.add_argument('-i', '--pdf_index_template_file', type=str, default='index_template.pdf', help='the pdf index form to populate')
    p.add_argument('-v', '--graduates_csv_file', type=str, default='graduates.csv', help='the csv file with the graduate data')
    p.add_argument('-e', '--certificates_directory', type=str, default='certificates', help='the directory where the new certificates will be copied')
    p.add_argument('-g', '--certificates_global_fields', type=str, default='', help='certificates global fields expressed as JSON string')
    p.add_argument('-o', '--cert_names_csv_column', type=str, default='name', help='use this column from csv file for naming the certificates')
    args, _ = p.parse_known_args()
    return args


def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()
    #populate_pdf_certificates(conf)
    cert_hashes = hash_certificates(conf)
    create_certificates_index(conf, cert_hashes)

if __name__ == "__main__":
    main()
