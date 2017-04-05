## Create PDF certificates using an index document
This method allows an institution to issue digital certificates. It creates PDF certificate files and issues a hash representing those files into the Bitcoin network's blockchain. The general process is as follows:
  - A PDF template file is populated using a CSV that contains all the graduates; a PDF certificate is created for each entry in the CSV
  - All the certificates are hashed (sha256) and their hashes are included in an index PDF document that is created from scratch using the configuration file
  - The index document is hashed and that hash is published into the blockchain

## Requirements
To use one needs to satisfy the following:
  - Have a local Bitcoin node running (testnet or mainnet)
  - Have python 3 installed and knowledge on using virtualenv
  - Have a Java Runtime Environment available -- note that most systems have one by default
    - this was necessary to properly handle UTF-8 characters while populating the certificate; no python OS project could handle this
  - Basic knowledge of the operating system (examples are given on a Debian-based linux system)

## Installation
Create a new python virtual environment

`$ python3 -m venv new_py3_env`

Activate new environment

`$ source new_py3_env/bin/activate`

Get the code from github and go to that directory (a package python might be created in the future)

`$ git clone https//github.com/UniversityOfNicosia/blockchain-certificates.git && cd blockchain-certificates`

Run setup to install

`$ pip install .`


## Scripts and Usage
The relevant scripts that will be made available are `create-certificates-with-index` and `publish-hash`. Both take several command-line options and option `-h` provides help. However, we do strongly recommend to use a config file to configure the scripts. Both scripts use the same configuration file since they share options. You can then, if needed, use some of the command-line options to override options from the configuration file.

In addition to setting up the configuration file (consult the following section) one needs to provide:

__Pdf certificate template__
:	This is the PDF certificate template that will be used to create all the certificates. It will consist of the certificate exactly as you want it displayed with placeholders to be filled in for each graduates (e.g. graduate's name and grade, etc.). The placeholders are just Acroform fields. Any version of Acrobat Pro is required to create the (Acroform) fields. The fields need to have the same name as the column headers in the CSV file that are expected to match.

__CSV graduates file__
:	This is a CSV file that contains all the fields required to populate the certificate template. It could contain extra columns that will be ignored. The header of the file should contain the names of the columns and those names are used to match the placeholder fields of the PDF template and fill them accordingly.

### Best Practices
We recommend to create a new folder (working directory) where everything will take place. Thus, all files used and all files created are organized properly in one place.

Example:
```
working_directory
      |--- certificate_template.pdf
      |--- graduates.csv
      `--- config.ini
```

### Usage: `create-certificates-with-index`
Creates the certificates given a PDF template file and a CSV file that contains all the graduates; a PDF certificate is created for each entry in the CSV. It then hashes all the certificates (sha256) and their hashes are included in an index PDF document that is created from scratch using the configuration file.

Given the example directory structure from above and a proper config.ini file it is as simple as:

```
$ create-certificates-with-index -c path/to/working_directory/config.ini
```

The script will confirm the arguments passed and then it will create all the certificates and the index document.


### Usage: `publish-hash`
Hashes the index document and that hash is published into the blockchain. The transaction id is returned, which can be used to confirm publication in any Bitcoin blockchain explorer.

Given the example directory structure from above and a proper config.ini file it is as simple as:

```
$ publish-hash -c path/to/working_directory/config.ini
```

## Configuration Options (config.ini)

|Option|Explanation and example|
|------|-----|
|**Global**||
|working_direcory|The working directory for issuing the certificates. All paths/files are always relative to this directory. Example: `/home/kostas/spring_2016_graduates`|
|**PDF certificates related**||
|pdf_cert_template|The name of the PDF template file relative to `working_directory`. Example: `certificate_template.pdf`|
|graduates_csv_file|The name of the comma separated value file that contains individual information for each graduate. It is relative to `working_directory`. Example: `graduates.csv`|
|certificates_directory|The directory were all the new certificates will be stored. It is recommended that this directory is always empty before running the script. If it doesn't exist it will be created. It is relative to `working_directory`. Example: `certificates`|
|certificates_global_fields|A simple key-value object that contains data for the `pdf_cert_template` to fill in fields that are common to all graduates. Given that there is a field called `date ` for the date that the certificate was awarded an example would be: `{"date": "5 Dec 2016"}`|
|**PDF index file creation related**|*Note: since the number of hashes is variable it was not possible to create the index file using an Acroform PDF template. The only way was to use XFA dynamic forms but those are propriatery standards and only a small minority of viewers can properly deal with them. We thus decided to create the (relatively) simple index file programmatically. This section contains simple configuration on what the index file would contain. It might be improved with images/logos and/or more fine-grained parameterization in the future.*|
|output_pdf_index_file|The name of the PDF index file to be created. It is relative to `working_directory`. Example: `index_document.pdf`|
|institution_name|The name of the institution used in the creation of the `output_pdf_index_file`. Example: `UNIVERSITY OF NEVERLAND`|
|index_title|The title of the award used in the creation of the `output_pdf_index_file`. Example: `INDEX OF CERTIFICATES AWARDED TO THE STUDENTS WHO SUCCESSFULLY COMPLETED THE MC101 INTRODUCTION TO MAGICAL CREATURES, AUTUMN 2016.`|
|index_issuing_text|Details of issuance used in the creation of the `output_pdf_index_file`. Example: `A SHA-256 hash of this index document has been stored in the Bitcoin blockchain on January 19, 2017, in a transaction that will originate from address mgs9DLttzvWFkZ46YLSNKSZbgSNiMNUsdJ and will also be announced through the University of Neverland's website.`
|index_validation_text|Text that describes the process of manually validating a certificate. It is provided in comma separated text to allow for spaces between sentences. Example: `[To verify the authenticity of a presented certificate please follow these steps:, (1) Confirm the authenticity of the index document:, (a) Ensure that you are using a valid index document supplied by the University of Neverland, (b) The index document PDF can be found at : http://neverland.ac.ea/certificates and at other online locations distributed by the University of Neverland, (c) The validity of the index document can be confirmed by reviewing the OP_RETURN field in a blockchain transaction confirmed on January 19 2017., , The SHA-256 hash of the valid index document prepended by "ULand " (554c616e6420 in hex encoding) will be found in one transaction during that day, , (2) Confirm the authenticity of the certificate:, (a) Produce a SHA-256 hash of the PDF certificate to be authenticated using any method or any online tool, (b) Search for the certificate's SHA-256 hash within the authenticated index document.,  , If the hash is found then the certificate is authentic.]`|
|**CSV file related**||
|cert_names_csv_column|Specifies the header of the column to use to name the certificates filenames. It has to be unique for each row or else the latter certificates will overrite the former! A good approach is to use a graduate identifier or their name. Given that `graduates_csv_file` contains a column with header `name` with all the (unique) names of the graduates an example value would be: `name`
|**Blockchain related**|*Note: currently only Bitcoin's blockchain is supported.*|
|issuing_address|The Bitcoin (testnet or mainnet) address to use for creating the OP_RETURN transaction that will issue the index document's hash in the blockchain. It has to have sufficient funds to cover just the fees of the transaction. If more funds are present we send them back as change to the same address. Make sure that you have the private key for this address safe since that might be the only formal way of proving who issued the certificates. Example for testnet: `mgs9DLttzvWFkZ46YLSNKSZbgSNiMNUsdJ`|
|full_node_url|The URL of the full node together with the port. Example for testnet: `127.0.0.1:18332`
|full_node_rpc_user|The name of the RPC user as configured in bitcoin.conf of the full node. Note that the RPC password is going to be asked when running the `publish-hash` script. Example: `kostasnode`|
|testnet|Specifies whether it will use testnet of mainnet to issue the hash. Example: `true`|
|tx_fee_per_byte|Specifies the mining fee to use per byte of the transaction's size. Consult https://bitcoinfees.21.co or another site for possible values. Example value on Jan 2017 is: `100`|
|hash_prefix|It is possible to prepend the index document's hash with a value to differentiate this OP_RETURN transaction from others. You should provide directly the hex value here using any online conversion tool to convert to hex. It is optional and you can comment it out for no prefix. Example value for prepending the string "ULand " is: `554c616e6420`.

## Example project to experiment
The `sample_working_dir_with_index` directory in the root of the project contains everything needed to create the PDF certificates and the index file. Just delete `index_document.pdf` and the `certificates` directory and run the process again to create them. Note that the sample `config.ini` needs to be updated with the path where the `sample_working_dir_with_index` directory is as well as with the proper Bitcoin address and RPC user name for the actual issuing. We recommend using testnet until you feel comfortable.

