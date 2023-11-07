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


# Stop current instance of unicorn
# pstree -ap | grep gunicorn | awk -F',' '{print $2}' | awk -F' ' '{print $1}' | head -n 1 | xargs -r kill
pstree -ap | grep autosubmit_api | awk -F',' '{print $2}' | awk -F' ' '{print $1}' | head -n 1 | xargs -r kill
pstree -ap | grep autosubmit_api 
# pstree -ap | grep gunicorn 

# activate conda environment
conda activate autosubmit_api

# if update to a new version we install it from pip
if [ "${UPDATE}" = true ]; then
   pip install ./AS_API_4
fi

# prepare to launch
echo "Set SECRET KEY"
export AUTHORIZATION_LEVEL='NONE'
echo "Set SECRET KEY"
export SECRET_KEY='c&X=<dFoz^ym}_^{jvma'
echo "Set CAS LOGIN URL"
export CAS_LOGIN_URL='https://cas.bsc.es/cas/login'
echo "Set CAS VERIFY URL"
export CAS_VERIFY_URL='https://cas.bsc.es/cas/serviceValidate'
echo "Gunicorn starting in 3 seconds..."
sleep 3
LOG_NAME="$(date '+%Y%m%d%H%M')logunicorn.yml"
echo "${LOG_PATH}/${LOG_NAME}"

# NOTE: for debugging remove the --preload option from the command line invokation

autosubmit_api start --log-file ${LOG_PATH}/${LOG_NAME} -w 6 -b 127.0.0.1:8081 --daemon

# gunicorn --log-file=-  --error-logfile ${LOG_PATH}/${LOG_NAME} --timeout 600 -b 0.0.0.0:8081 -w 6 "AS_API_4.autosubmit_api.app:create_app()"  --preload --daemon

#set +xv
