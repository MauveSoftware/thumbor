#!/bin/sh
# based on https://github.com/MinimalCompact/thumbor

envtpl /etc/circus.d/thumbor-circus.ini.tpl  --allow-missing --keep-template

if [ ! -f /app/thumbor.conf ]; then
  envtpl /app/thumbor.conf.tpl  --allow-missing --keep-template
fi

# If log level is defined we configure it, else use default log_level = info
if [ -n "$LOG_LEVEL" ]; then
    LOG_PARAMETER="-l $LOG_LEVEL"
fi

# Check if thumbor port is defined -> (default port 8888)
if [ -z ${THUMBOR_PORT+x} ]; then
    THUMBOR_PORT=8888
fi

if [ "$1" = 'thumbor' ] || [ "$1" = 'circus' ]; then
    if [ "${THUMBOR_NUM_PROCESSES:-1}" -gt "1" ]; then
        echo "---> Starting thumbor circus with ${THUMBOR_NUM_PROCESSES} processes..."
        exec /usr/local/bin/circusd /etc/circus.ini
    else
        echo "---> Starting thumbor solo..."
        exec thumbor --port=$THUMBOR_PORT --conf=/app/thumbor.conf $LOG_PARAMETER
    fi
fi

exec "$@"
