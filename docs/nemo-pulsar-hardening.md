# NEMO Pulsar Deployment Hardening

## Current Setup

Pulsar runs manually on NEMO login2 via `nohup`. This works but requires
manual restart after node reboots or crashes.

## Why Not systemd?

NEMO login nodes do not have user-level systemd available:

```
$ systemctl --user status
Failed to connect to bus: No medium found
```

System-level systemd would require RZ (Rechenzentrum) to set up a service,
which is outside the scope of this project.

## Current Workaround: Auto-Restart Wrapper

A wrapper script (`start_pulsar.sh`) provides automatic restart on crash:

```bash
#!/bin/bash
cd /home/fr/fr_ds722/pulsar
source .venv/bin/activate

while true; do
    echo "$(date): Starting Pulsar..." >> pulsar.log
    pulsar-main --app_conf_path config/app.yml >> pulsar.log 2>&1
    echo "$(date): Pulsar exited, restarting in 10s..." >> pulsar.log
    sleep 10
done
```

Start it:
```bash
nohup ~/pulsar/start_pulsar.sh &
echo $! > ~/pulsar/pulsar.pid
```

Stop it:
```bash
kill $(cat ~/pulsar/pulsar.pid)
```

## Proper Hardening Options

1. **Ask RZ** to create a system-level systemd service for Pulsar on login2
2. **Run Pulsar as a Slurm job** — submit it as a long-running job on a compute
   node; Slurm will restart it if it dies (CVMFS availability on that node
   needs to be verified)
3. **Containerize Pulsar** on login2 using Apptainer — Björn suggested this;
   would isolate the environment and simplify deployment

## Notes

- Pulsar must run on **login2** specifically, not login1, because CVMFS
  (`/cvmfs/singularity.galaxyproject.org/all/`) is only mounted on login2
  and compute nodes
- The SSH reverse tunnel for Galaxy file transfers must also be active:
  `ssh -R 8080:192.168.2.6:8080 fr_ds722@login2.nemo.uni-freiburg.de`
