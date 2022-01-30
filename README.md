# dynamic-flag-ctfd-framework

## Labels
* `dynamic-label=true` : enable dynamic challenge
* `challenge-name`: name of the challenge
* `flag-localization` : localization of the file where the flag is
* `flag-script` : script that it's called with the flag to update it

## ENV 
* `CTFD_URL` : CTFd endpoint ending with  /api/v1
* `TOKEN` : Token

## Test
```
docker run --rm -it -l "dynamic-label=true" alpine /bin/bash
```