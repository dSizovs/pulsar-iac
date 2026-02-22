# Galaxy-Pulsar Distributed Compute Cluster

This repository contains the Infrastructure as Code (IaC) and core configuration files for a production-grade Galaxy server routing jobs to remote Pulsar compute nodes via AMQP (RabbitMQ).

## Architecture Overview
* **Master Node:** Galaxy 23.x+ running with dedicated Celery job handlers managed via Gravity.
* **Message Broker:** RabbitMQ handling heartbeat and status callbacks via `pulsar_mq` plugins.
* **Job Router:** Total Perspective Vortex (TPV) natively routing tools to execution environments.
* **Compute Nodes:** Remote Pulsar workers executing isolated jobs using rootless Apptainer containers.

## Repository Structure
* `pulsar.yml`: Ansible playbook to automate the deployment of remote Pulsar nodes and RabbitMQ.
* `group_vars/`: Ansible variable definitions for the Pulsar deployment.
* `galaxy_configs/`: Core Galaxy configurations required for distributed compute:
  * `galaxy.yml`: Defines Gravity process management, including dedicated database-monitoring job handler processes (`handler_0`, `handler_1`) and the internal AMQP listener.
  * `job_conf.xml`: Modern Galaxy job configuration mapping tools to TPV and defining the AMQP destinations.
  * `tpv_rules_local.yml`: Dynamic routing rules mapping specific tools (e.g., `ChangeCase`) to specific Pulsar destinations.

## Deployment Notes
When configuring the Galaxy master server, ensure that the `galaxy_configs` files are placed in the `~/galaxy/config/` directory and that the Gravity process manager is explicitly updated (`galaxyctl update`) to register the background handler threads.
