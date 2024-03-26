### 0.2.2 / 2023-27-03 ###
- Added `sha_384` as hash algorithm for the signature authentication.
- Drop Python 3.6 from CI. It has been unsupported since December 2021 and github actions runner don't support anymore (https://github.com/actions/setup-python/issues/544)

### 0.2.1/ 2022-29-08 ###

* Add documentation on publishing releases
* Avoid creating a new Assembly when a rate limit error is received from fetching an Assembly too frequently

### 0.2.0/ 2022-21-06 ###

* Drop Python versions before 3.7 as they are unsupported
* Update code to Python 3 syntax
* Prevent rate limiting when polling Assembly status

### 0.1.12/ 2020-14-12 ###

* Send `transloadit-client` header along with requests

### 0.1.10/ 2018-27-08 ###

* Drop the use of requirements.txt for dependencies
* Update dependency versions

### 0.1.9/ 2018-12-04 ###

* Loosen request module's version

### 0.1.8/ 2018-19-03 ###

* Update tuspy version
* Increase upload chunk size
