blockchain-certificates
=======================

This project allows an institution to issue digital certificates. It
creates pdf certificate files (or uses existing ones) and issues a hash
representing those files into the Bitcoin network's blockchain. It can 
do so in two ways; one using an index file to aggregate the 
certificates' hashes and the other that does not require an index file.
The former is the method used in the past and we do **recommend using 
the new method** as it supersedes the old ones. The only advantage of
the old process over the new is that it is easier to verify manually.

--------------

More information on creating certificates 
(**recommended**):

https://github.com/UniversityOfNicosia/blockchain-certificates/blob/master/docs/create_certificates.md

--------------

More information on issuing existing certificates:

https://github.com/UniversityOfNicosia/blockchain-certificates/blob/master/docs/issue_certificates.md

--------------

More information on creating certificates with an index file
(deprecated):

https://github.com/UniversityOfNicosia/blockchain-certificates/blob/master/docs/create_certificates_with_index.md
