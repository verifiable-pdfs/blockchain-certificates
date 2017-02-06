# Blockchain Certificates
This project allows an institution to issue digital certificates. It creates pdf certificate files and issues a hash representing those files into the Bitcoin network's blockchain. The general process is as follows:
  - A pdf template file is populated using a CSV that contains all the graduates; a pdf certificate is created for each entry in the CSV
  - All the certificates are hashed (sha256) and their hashes are included in an index pdf document that is created from scratch using the configuration file
  - The index document is hashed and that hash is published into the blockchain

## Requirements
To use one needs to satisfy the following:
  - Have a local Bitcoin node running (testnet or mainnet)
  - Have python 3 installed and knowledge on using virtualenv
  - Basic knowledge of the operating system (examples are given on a Debian-based linux system)

## Installation
1. Create a new python virtual environment
`$ python3 -m venv new_py3_env`

2. Activate new environment
`$ source new_py3_env/bin/activate`

3. Get the code from github and go to that directory (a package python might be created in the future)
`$ git clone https//github.com/UNIC/PROJ... && cd PROJ`

4. Run setup to install
`$ pip install .`


## Scripts
Two scripts will be made available, `create-certificates` and `publish-hash`. Both take several command-line options and option `-h` provides help. However, we do strongly recommend to use a config file to configure the scripts. Both scripts use the same configuration file since they share options. You can then, if needed, use some of the command-line options to override options from the configuration file.

### Notes on `create-certificates`
Creates the certificates given a pdf template file and a CSV file that contains all the graduates; a pdf certificate is created for each entry in the CSV. It then hashes all the certificates (sha256) and their hashes are included in an index pdf document that is created from scratch using the configuration file.

EXPLAIN pdf template acroform...
EXPLAIN CSV file
EXPLAIN pdf index file created from scratch
EXPLAIN config.ini options for above

### Notes on `publish-hash`
Hashes the index document and that hash is published into the blockchain.

EXPLAIN that the issuing_address needs to either be created by the local node or imported to the local node. PLUS it needs funds!
EXPLAIN config.ini options for above

Tell them how check that hash is on the blockchain

## Example usage








