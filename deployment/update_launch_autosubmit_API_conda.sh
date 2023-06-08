#!/bin/bash
. ~/.bashrc

LOG_PATH=${PLOG}
UPDATE=false

while getopts ":e:u" opt; do
  case "$opt" in
    u)  UPDATE=true;
      ;;
   esac
done


# Stop current instance of unicorn
pstree -ap | grep gunicorn | awk -F',' '{print $2}' | awk -F' ' '{print $1}' | head -n 1 | xargs -r kill
pstree -ap | grep gunicorn

# activate conda environment
conda activate autosubmit_api

# if update to a new version we install it from pip
if [ "${UPDATE}" = true ]; then
   pip install autosubmit_api --upgrade
fi

# prepare to launch
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
gunicorn --error-logfile ${LOG_PATH}/${LOG_NAME} --timeout 600 -b 0.0.0.0:8081 -w 6 autosubmit_api.app:app --preload --daemon
