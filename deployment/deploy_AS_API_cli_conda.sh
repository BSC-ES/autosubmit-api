#!/bin/bash
. ~/.bashrc

#set -xv

LOG_PATH=${PLOG}
UPDATE=true

while getopts ":e:u" opt; do
  case "$opt" in
    u)  UPDATE=true;
      ;;
   esac
done

# activate conda environment
conda activate autosubmit_api

# Stop current instance of unicorn
# pstree -ap | grep gunicorn | awk -F',' '{print $2}' | awk -F' ' '{print $1}' | head -n 1 | xargs -r kill
echo "Stopping current instances of autosubmit_api..."
pstree -ap | grep autosubmit_api | awk -F',' '{print $2}' | awk -F' ' '{print $1}' | head -n 1 | xargs -r kill
sleep 3
pstree -ap | grep autosubmit_api 
# pstree -ap | grep gunicorn 

# if update to a new version we install it from pip
if [ "${UPDATE}" = true ]; then
   pip install ./AS_API_4
fi

# prepare to launch
echo "Set SECRET KEY"
export PROTECTION_LEVEL='ALL'
echo "Set SECRET KEY"
export SECRET_KEY='c&X=<dFoz^ym}_^{jvma'
echo "Set CAS LOGIN URL"
export CAS_LOGIN_URL='https://cas.bsc.es/cas/login'
echo "Set CAS VERIFY URL"
export CAS_VERIFY_URL='https://cas.bsc.es/cas/serviceValidate'
echo "Gunicorn starting in 2 seconds..."
sleep 2
LOG_NAME="$(date '+%Y%m%d%H%M')logunicorn.yml"
echo "${LOG_PATH}/${LOG_NAME}"

autosubmit_api start --log-file ${LOG_PATH}/${LOG_NAME} -w 2 -b 0.0.0.0:8081 --daemon --log-level DEBUG
