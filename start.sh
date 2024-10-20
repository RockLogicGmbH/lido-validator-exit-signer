#! /usr/bin/env bash
set -e

#
# Parse command-line arguments
#

DEV_AUTO_SSL=false
if [ -z "$FORCE_SSL" ]; then
    FORCE_SSL=false
else
    FORCE_SSL=true
fi
while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto-ssl)
            DEV_AUTO_SSL=true
            shift
            ;;
        --force-ssl)
            FORCE_SSL=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

#
# PRE-START TASKS
#

# Auto enable self-signed SSL in dev mode
if ( [ -z "$__DOCKERIZED__" ] && [ $DEV_AUTO_SSL = true ] ) || [ $FORCE_SSL = true ]; then
    export EXSI_SV_SSL_CERTFILE="certs/selfsigned.crt"
    export EXSI_SV_SSL_KEYFILE="certs/selfsigned.key"
    export SV_SSL_CERTFILE="certs/selfsigned.crt"
    export SV_SSL_KEYFILE="certs/selfsigned.key"
fi

# Auto create a self-signed SSL cert if not existent or expired (usage is optional)
# if ! [ -f "certs/selfsigned.crt" ] || ! [ -f "certs/selfsigned.key" ] || ! openssl x509 -checkend 0 -noout -in "certs/selfsigned.crt" &>/dev/null; then
#     openssl req -x509 -nodes -days 365 -newkey rsa:2048 -subj "/C=AT/ST=MyState/L=MyCity/O=MyOrg/OU=MyOrgUnit/CN=MyHostName" -keyout certs/selfsigned.key -out certs/selfsigned.crt &>/dev/null
# fi
# Q&D workarround, run from within python shell for nicer logging
python ./prestart_gencert.py

#
# START THE APP
#

# Start App
export __STARTSCRIPT__="yes"
python ./main.py