#!/bin/bash
cd /home/fr/fr_ds722/pulsar
source .venv/bin/activate

while true; do
    echo "$(date): Starting Pulsar..." >> pulsar.log
    pulsar-main --app_conf_path config/app.yml >> pulsar.log 2>&1
    echo "$(date): Pulsar exited, restarting in 10s..." >> pulsar.log
    sleep 10
done
