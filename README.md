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

## Manual Code Patches Required

Phase 4 uses pulsar-relay which is brand-new and not yet fully supported 
in stable releases. Two manual patches are required:

**1. Upgrade pulsar-app to dev version (on Galaxy VM):**
```bash
~/galaxy/.venv/bin/pip install git+https://github.com/galaxyproject/pulsar.git
```

**2. Patch Galaxy's Pulsar runner to accept relay parameters:**

File: `~/galaxy/lib/galaxy/jobs/runners/pulsar.py`

Find the `PULSAR_PARAM_SPECS` dict and add after the `amqp_key_prefix` block:
```python
    relay_url=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    relay_username=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    relay_password=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    relay_topic_prefix=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
```

> **Note:** If you're on a newer Galaxy release, this patch may not be needed
