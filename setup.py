from setuptools import setup
from blockchain_certificates import __version__

with open('README.rst') as readme:
    long_description = readme.read()

setup(name='blockchain-certificates',
      version=__version__,
      description='Create pdf certificate files and issue on the blockchain!',
      long_description=long_description,
      author='Konstantinos Karasavvas',
      author_email='kkarasavvas@gmail.com',
      url='https://github.com/verifiable-pdfs/blockchain-certificates',
      license='AGPLv3',
      packages=['blockchain_certificates'],
      install_requires=[
          "pdfrw==0.3",
          "fpdf==1.7.2",
          "configargparse==0.11.0",
          "merkletools==1.0.3",
          "bitcoin-utils==0.4.7",
          "litecoin-utils==0.4.8",
          #"python-bitcoinrpc==1.0", #installed from bitcoin-utils
          # install litecoinrpc since it is not auto install from litecoin-utils
          # probably because wheel does not exist; because does not work on git
          # repos. Could later clone litecoinrpc and put it in pypi myself
          "litecoinrpc @ git+git://github.com/bitwyre/python-litecoinrpc@f9deb63"
      ],
      package_data={
          'blockchain_certificates': ['requirements.txt',
                                      'java/FillPdf.java',
                                      'java/FillPdf.class'],
      },
      include_package_data=True,
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'create-certificates = blockchain_certificates.create_certificates:main',
              'validate-certificates = blockchain_certificates.validate_certificates:main',
              'issue-certificates = blockchain_certificates.issue_certificates:main',
              'revoke-certificates = blockchain_certificates.revoke_certificates:main'
          ]
      },
      keywords='blockchain academic certificates'
     )

