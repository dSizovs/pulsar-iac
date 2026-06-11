# Galaxy-Pulsar Distributed Compute Cluster

Infrastructure and configuration for routing **usegalaxy.eu** jobs to a remote HPC (NEMO/Slurm) using the experimental **pulsar-relay** mode; no RabbitMQ or AMQP required.

## Architecture

usegalaxy.eu -> pulsar-relay (bw-cloud VM:9000) -> Pulsar (NEMO login node) -> Slurm -> compute nodes

Tools run in Singularity/Apptainer containers pulled from CVMFS. The relay brokers messages by HTTP long-polling, so the cluster needs no inbound ports.

## Repository layout

- `roles/pulsar_relay/` Ansible role that deploys the relay (venv, systemd unit, Valkey backend)
- `pulsar_relay.yml` playbook entry point
- `nemo_config/` Pulsar config for the NEMO login node (`app.yml`, `job_metrics_conf.xml`, `start_pulsar.sh`)
- `docs/` failure-testing results and hardening notes

## Deploy the relay

```bash
ansible-playbook pulsar_relay.yml -i <inventory>
```

Secrets (admin password, JWT secret) are supplied at deploy time / from the usegalaxy.eu vault, the files here use placeholders.

## Notes

- Manager must be `queued_cli` with `job_plugin: Slurm` — `queued_python` runs on the login node, which is not allowed on shared HPC.
- The `pulsar_eu_nemo` runner and `pulsar_nemo_tpv` TPV destination live in `usegalaxy-eu/infrastructure-playbook`.
- Operations / maintenance doc: `usegalaxy-eu/operations`.

## Status

Experimental. Pin a Pulsar version known to work with the cluster's Python and the relay transport.
