'''
Populates the required pdf form templates: both for individual certificates and for the hash index.
'''
import os
import sys
import glob
import configargparse
from blockchain_certificates import pdf_utils



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
    p.add_argument('-o', '--output_pdf_index_file', type=str, default='index_document.pdf', help='the name of the pdf index document that will be created')
    p.add_argument('-i', '--institution_name', type=str, help='the name of the institution to display in the the index document')
    p.add_argument('-t', '--index_title', type=str, help='the title of the index document')
    p.add_argument('-s', '--index_issuing_text', type=str, help='the text describing date and address of transaction')
    p.add_argument('-x', '--index_validation_text', type=str, action='append', help='the text describing the process of validating the certificate')
    p.add_argument('-v', '--graduates_csv_file', type=str, default='graduates.csv', help='the csv file with the graduate data')
    p.add_argument('-e', '--certificates_directory', type=str, default='certificates', help='the directory where the new certificates will be copied')
    p.add_argument('-g', '--certificates_global_fields', type=str, default='', help='certificates global fields expressed as JSON string')
    p.add_argument('-f', '--cert_names_csv_column', type=str, default='name', help='use this column from csv file for naming the certificates')
    args, _ = p.parse_known_args()
    return args


def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()
    pdf_utils.populate_pdf_certificates(conf, False)

    # get certificate file list 
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    cert_files = glob.glob(certificates_directory + os.path.sep + "*.pdf")

    cert_hashes = pdf_utils.hash_certificates(cert_files)
    pdf_utils.create_certificates_index(conf, cert_hashes)

if __name__ == "__main__":
    main()
