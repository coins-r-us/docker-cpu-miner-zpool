#!/bin/sh

if [ -z ${WORKERNAME+x} ]; then
        WORKERNAME=$(
(hostname -f;echo _$(id -u|base64)_$(uname -m) ) |sed 's/ //g'|tr -cd '[:alnum:]_'|tr -d '\n\t\t'
)
fi


echo "WALLET: $WALLET"
echo "WORKERNAME: $WORKERNAME"
echo "PAYOUTMETHOD: ${PAYMETH}" 
echo "MAXTHREADS: ${MAXTHREADS}"
echo "WAITTIME: ${WAITTIME}" 

while (true);do 

/bin/bash -c "timeout -t 7200 python3 cpuminer_driver.py $WALLET $PAYMETH $WORKERNAME $MAXTHREADS $WAITTIME"
done
