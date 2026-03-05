# Galaxy-Pulsar Distributed Compute Cluster

This repository contains the Infrastructure as Code (IaC) and core configuration files for a production-grade Galaxy server routing jobs to remote HPC compute nodes (via Slurm) using Pulsar and AMQP (RabbitMQ).


## Architecture Overview
* **Master Node:** Galaxy 23.x+ running with dedicated Celery job handlers managed via Gravity.
* **Message Broker:** RabbitMQ handling job dispatch, heartbeats, and status callbacks via the `pulsar_mq` plugin.
* **Job Router:** Total Perspective Vortex (TPV) dynamically routing specific tools to distinct execution environments.
* **Network Bridge:** Double-barrel reverse SSH tunnels (Ports 5672 & 8080) bypassing strict HPC firewalls to route AMQP and HTTP file transfers.
* **Compute Nodes:** Remote Pulsar workers executing isolated jobs on Slurm using rootless Apptainer containers.

## Repository Structure
* `pulsar.yml` & `group_vars/`: Ansible playbooks and variables to automate the deployment of baseline Pulsar nodes and RabbitMQ.
* `galaxy_configs/`: Core Galaxy configurations required for distributed compute:
  * `galaxy.yml`: Defines Gravity process management, job handler threads, and internal AMQP listeners.
  * `job_conf.xml`: Job configuration defining the TPV dispatcher, runner plugins, and tunnel URLs.
  * `tpv_rules_local.yml`: Dynamic routing rules mapping tools (e.g., `ChangeCase`) to specific HPC destinations with `requests` transport.
* `nemo_config/`: Manual worker configuration (`app.yml`) required for deployment on strictly firewalled, 2FA-secured HPC clusters where Ansible cannot reach.

## HPC Deployment & Execution
When routing to a strictly firewalled HPC cluster, the connection relies on an active SSH tunnel. Ensure Galaxy is running, then execute the following:

**1. Open the Reverse Tunnels (From Local Machine):**
```bash
IP=$(multipass info vm-galaxy --format json | jq -r '.info."vm-galaxy".ipv4[0]')
ssh -R 5672:$IP:5672 -R 8080:$IP:8080 username@login.nemo.uni-freiburg.de
```

**2. Start the Webless AMQP Worker (On Remote HPC):**
```bash
cd pulsar
source .venv/bin/activate
pulsar-main --app_conf_path config/app.yml
```
