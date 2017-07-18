from setuptools import setup
from pip.req import parse_requirements
from blockchain_certificates import __version__


install_reqs = parse_requirements('requirements.txt', session=False)
requirements = [str(ir.req) for ir in install_reqs]

with open('README.rst') as readme:
    long_description = readme.read()

setup(name='blockchain-certificates',
      version=__version__,
      description='Create pdf certificate files and issue on the blockchain!',
      long_description=long_description,
      author='Konstantinos Karasavvas',
      author_email='kkarasavvas@gmail.com',
      url='https://github.com/UniversityOfNicosia/blockchain-certificates',
      license='AGPLv3',
      packages=['blockchain_certificates'],
      install_requires=requirements,
      package_data={
          'blockchain_certificates': ['java/itextpdf-5.5.10.jar',
                                      'java/ITEXTPDF-LICENSE.txt',
                                      'java/json-simple-1.1.1.jar',
                                      'java/JSON-SIMPLE-LICENSE.txt',
                                      'java/FillPdf.java',
                                      'java/FillPdf.class'],
      },
      include_package_data=True,
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'create-certificates-with-index = blockchain_certificates.create_certificates_with_index:main',
              'publish-index-hash = blockchain_certificates.publish_hash:main',
              'create-certificates = blockchain_certificates.create_certificates:main',
              'validate-certificates = blockchain_certificates.validate_certificates:main',
              'issue-certificates = blockchain_certificates.issue_certificates:main'
          ]
      },
      keywords='blockchain academic certificates'
     )

