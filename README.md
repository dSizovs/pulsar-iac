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
