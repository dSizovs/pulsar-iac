# Galaxy-Pulsar Distributed Compute Cluster

Infrastructure and configuration for routing Galaxy jobs to a remote HPC (NEMO/Slurm) using the experimental **pulsar-relay** mode; no RabbitMQ or AMQP required.

## Architecture

Galaxy (VM:8080) -> pulsar-relay (VM:9000) -> SSH tunnel -> Pulsar (NEMO) -> Slurm -> NEMO localhost:9555

File transfers go directly between Pulsar and Galaxy via HTTP, bypassing the relay.

## How to Run

**1. Start the relay (Galaxy VM):**
```bash
cd ~/pulsar-relay && python start_relay.py
```

**2. Open SSH tunnel (local machine):**
```bash
ssh -R 9555:<vm-ip>:9000 -R 8080:<vm-ip>:8080 username@login.nemo.uni-freiburg.de
```

**3. Start Pulsar (NEMO):**
```bash
cd pulsar && source .venv/bin/activate && pulsar-main --app_conf_path config/app.yml
```

**4. Start Galaxy (VM):**
```bash
cd ~/galaxy && sh run.sh
```

## Manual Patches Required

**1. Upgrade pulsar-app to dev version (on Galaxy VM):**
```bash
~/galaxy/.venv/bin/pip install git+https://github.com/galaxyproject/pulsar.git
```

**2. Patch Galaxy's container resolver to handle read-only CVMFS:**

File: `~/galaxy/lib/galaxy/tool_util/deps/container_resolvers/mulled.py`

Find `safe_makedirs(self.cache_directory.path)` and wrap it:
```python
try:
    safe_makedirs(self.cache_directory.path)
except PermissionError:
    pass
```

This prevents Galaxy from crashing when the CVMFS container cache is read-only on the compute cluster.
