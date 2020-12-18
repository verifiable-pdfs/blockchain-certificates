## Create PDF certificates 
This method allows an institution to issue digital certificates. It creates PDF certificate files and issues a hash representing those files into the Bitcoin network's blockchain. The general process is as follows:
  - A PDF template file is populated using a CSV that contains all the graduates; a PDF certificate is created for each entry in the CSV
  - The PDF certificates are hashed (sha256) and a merkle tree is created, the merkle root of which is published into the blockchain

## Requirements
To use one needs to satisfy the following:
  - Have a local Bitcoin node running (testnet or mainnet)
  - Have python 3 installed and knowledge on using virtualenv
  - Have a Java Runtime Environment available -- note that most systems have one by default
    - this was necessary to properly handle UTF-8 characters while populating the certificate; no python OS project could handle this
  - Download two java libraries required for the populating the pdfs: itextpdf-5.5.10.jar and json-simple-1.1.1.jar
    - place the libraries in blockchain_certificates/java directory
  - Basic knowledge of the operating system (examples are given on a Debian-based linux system)

## Installation
Create a new python virtual environment

`$ python3 -m venv new_py3_env`

Activate new environment

`$ source new_py3_env/bin/activate`

Get the code from github and go to that directory (a package python might be created in the future)

`$ git clone https://github.com/UniversityOfNicosia/blockchain-certificates.git && cd blockchain-certificates`

Run setup to install

`$ pip install .`


## Scripts and Usage
The script that will be made available is `create-certificates`. Optionally `validate-certificates` can be used after issuing to validate the certificates and `revoke-certificates` to revoke previously issued certificates. All take several command-line options and option `-h` provides help. However, we do strongly recommend to use a config file to configure the scripts. Both scripts use the same configuration file since they share options. You can then, if needed, use some of the command-line options to override options from the configuration file.

In addition to setting up the configuration file (consult the following section) one needs to provide:

__Pdf certificate template__
:	This is the PDF certificate template that will be used to create all the certificates. It will consist of the certificate exactly as you want it displayed with placeholders to be filled in for each graduates (e.g. graduate's name and grade, etc.). The placeholders are just Acroform fields. Any version of Acrobat Pro is required to create the (Acroform) fields. The fields need to have the same name as the column headers in the CSV file that are expected to match.

Typically we only have an issuer being the owner of all the certificates. Optionally, however, an issuer can issue certificates on behalf of others and in this case we can provide additional information per row to specify the identity of the owner. Specifically we need to pass /_/_OWNER_NAME/_/_, /_/_OWNER_PK/_/_ and /_/_OWNER_ADDRESS/_/_. The owners' verification is the responsibiity of the issuer.


__CSV file__
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

### Usage: `create-certificates`
Creates the certificates given a PDF template file and a CSV file that contains all the graduates; a PDF certificate is created for each entry in the CSV. The PDF metadata fields contain an `issuer` field with information about the issuer (name, Bitcoin address/identification). It also contains a `metadata` field which contains all the user-defined metadata fields specified in `cert_metadata_columns`. Following is the creation of a merkle tree that contains all the hashes of the certificates, the merkle root of which is published to the blockchain. A corresponding chainpoint receipt is added as metadata in the `chainpoint_proof` field in each PDF certificate. The compulsory metadata are `issuer`, and `chainpoint_proof`.

Given the example directory structure from above and a proper config.ini file it is as simple as:

```
$ create-certificates -c path/to/working_directory/config.ini
```

The script will confirm the arguments passed and then it will create all the certificates and publish the merkle root hash to the blockchain. The certificates are finished, self-contained and ready to be shared.


### Usage: `validate-certificates`
This script can be used to validate certificates issued in the past or issued by others. You pass the certificates that you want to validate as arguments and whether it was issued on mainnet or testnet.

Given the example directory structure from above and a proper config.ini file it is as simple as:

```
$ validate-certificates -c path/to/working_directory/config.ini -f cert1.pdf cert2.pdf cert3.pdf
```

### Usage: `revoke-certificates`
This script can be used to revoke certificates issued in the past (or even issuing addresses - see below). You can revoke either a complete batch of certificates by passing the transaction id of the issuance or you can revoke individual certificates by passing the PDF certificates themselves.

Given the example directory structure from above and a proper config.ini file it is as simple as:

```
$ revoke-certificates -c path/to/working_directory/config.ini -p cert1.pdf cert2.pdf 
```

To revoke a complete batch (all certificates from a past issuance) you need to pass the txid:

```
$ revoke-certificates -c path/to/working_directory/config.ini -b 88b4ee67fc4fb8cfceaa5d1a4b4d7fa549d82b17868e64c0e578bc93e50c6053
```

In case the issuing address is compromised but you still have it you can revoke the issuing address. Any issuing or revoking after an address revocation is ignored. It will revoke the issuing_address from the configuration file:

```
$ revoke-certificates -c path/to/working_directory/config.ini -s
```


## Configuration Options (config.ini)

|Option|Explanation and example|
|------|-----|
|**Global**||
|working_direcory|The working directory for issuing the certificates. All paths/files are always relative to this directory. Example: `/home/kostas/spring_2016_graduates`|
|**PDF certificates related**||
|pdf_cert_template|The name of the PDF template file relative to `working_directory`. Example: `certificate_template.pdf`|
|csv_file|The name of the comma separated value file that contains individual information for each awardee. It is relative to `working_directory`. Example: `graduates.csv`|
|certificates_directory|The directory were all the new certificates will be stored. It is recommended that this directory is always empty before running the script. If it doesn't exist it will be created. It is relative to `working_directory`. Example: `certificates`|
|certificates_global_fields|An object that contains data for the `pdf_cert_template` to fill in fields that are common to all graduates. Given that there is a field called `date ` for the date that the certificate was awarded an example would be: `{ "fields": [ { "date": { "label": "Date", "order": 2, "hide": false, "value": "5 Dec 2016" } } ] }`|
|issuer|The name of the issuer/institution. Example: `UNIVERSITY OF NEVERLAND`|
|expiry_date|The date of expiry (if any) expressed in Unix Epoch / UTC. Example: `1553929397`|
|**CSV file related**||
|cert_names_csv_column|Specifies the header of the column to use to name the certificates filenames. It has to be unique for each row or else the latter certificates will overrite the former! A good approach is to use a graduate identifier or their name. Given that `csv_file` contains a column with header `name` with all the (unique) names of the graduates an example value would be: `name`|
|cert_metadata_columns|Specifies the header of the columns and the respective data to be added in the `metadata` field for each individual certificate. Global fields, as specified by `certificates_global_fields` can also be specified here to be included in the metadata. Example: `{ "columns": [ { "student_name": { "label": "Student Name", "order": 1, "hide":false } } ] }`|
|**Validation related**||
|f|Specify the PDF certificates to be validated.|
|blockchain_services|For each supported blockchain one can specify the validation services to use and how many successes required. Example (and default): `{ "bitcoin": { "services": [ {"blockcypher":{} } ], "required_successes": 1} }`. Currently, blockchains supported are 'bitcoin', 'litecoin', 'bitcoin_testnet' and 'litecoin_testnet'. Bitcoin suports 'blockcypher', 'btcd' and 'custom_api': `... {"btcd": { "full_url": "http://user:password@127.0.0.1:18334" }}. Litecoin currently supports 'ltcd' and 'custom_api'.`|
|verify_issuer|Specify the methods that an issuer identity (Bitcoin address) can be validated. Example (and default): `{ "methods": [] }`. Possible values are ... { "domain": { "url": "http://kkarasavvas.com" } } and { "github": { "user": "karask", "gist_id": "db951671b1af6b1edd56df06f1b9109a" } } |
|**Revocation related**|Mutually exclusive options|
|p|Specify the PDF certificates that we need to revoke.|
|batch|Specify the transaction id of the issuance which we want to revoke/invalidate.|
|address|Specify the address which will be revoked/invalidated. Not implemented yet.|
|**Blockchain related**|*Note: currently only Bitcoin's blockchain is supported.*|
|blockchain|The blockchain network to anchor the hash data. Currently 'bitcoin' and 'litecoin' are supported.
|issuing_address|The blockchain (testnet or mainnet) address to use for creating the OP_RETURN transaction that will issue the documents merkle root hash in the blockchain. It should be either a legacy address or a native segiwit address and needs to have sufficient funds to cover just the fees of the transaction. If more funds are present we send them back as change to the same address. Make sure that you have the private key for this address safe since that might be the only formal way of proving who issued the certificates. Example for testnet: `mgs9DLttzvWFkZ46YLSNKSZbgSNiMNUsdJ`|
|full_node_url|The URL of the full node together with the port. Example for testnet: `127.0.0.1:18332`
|full_node_rpc_user|The name of the RPC user as configured in bitcoin.conf of the full node. Note that the RPC password is going to be asked during execution of the `create-certificates` script. Example: `kostasnode`|
|full_node_rpc_password|The password of the RPC user as configured in bitcoin.conf of the full node. Note that the RPC password is going to be asked during execution of the `create-certificates` script. Example: `kostastoolongtoguess`|
|testnet|Specifies whether it will use testnet of mainnet to issue the hash. Example: `true`|
|tx_fee_per_byte|Specifies the mining fee to use per byte of the transaction's size. Consult https://bitcoinfees.21.co or another site for possible values. Example value on Jan 2017 is: `100`|
|issuer_identifier|It is possible to specify a value (max 8 bytes/chars) that is added in the OP_RETURN transaction to differentiate the issuer. It is optional. Example value: "UNicDC ".

## Example project to experiment
The `sample_create_certs_dir` directory in the root of the project contains everything needed to create the PDF certificates. Just delete the `certificates` directory and run the process again to create them. Note that the sample `config.ini` needs to be updated with the path that the `sample_create_certs_dir` is as well as with the proper Bitcoin address and RPC user name for the actual issuing. We recommend using testnet until you feel comfortable.

