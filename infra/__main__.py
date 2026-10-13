from pathlib import Path

import pulumi
import pulumi_gcp as gcp
import pulumi_random as random

gcp_cfg = pulumi.Config("gcp")
cfg = pulumi.Config()
region = gcp_cfg.require("region")  # southamerica-east1 (Sao Paulo)
zone = gcp_cfg.require("zone")
node_image = cfg.require("nodeImage")
rust_image = cfg.require("rustImage")

apis = [
    gcp.projects.Service(f"api-{s}", service=f"{s}.googleapis.com", disable_on_destroy=False)
    for s in ("run", "compute", "artifactregistry")
]


# Redis on the cheapest VM (e2-micro), internal IP only reachable inside the VPC, password protected.
redis_password = random.RandomPassword("redis-password", length=32, special=False)

gcp.compute.Firewall(
    "allow-redis-internal",
    network="default",
    allows=[gcp.compute.FirewallAllowArgs(protocol="tcp", ports=["6379"])],
    source_ranges=["10.128.0.0/9"],  # default-network subnets (includes Cloud Run Direct VPC egress)
    target_tags=["redis"],
    opts=pulumi.ResourceOptions(depends_on=apis),
)

redis_startup = redis_password.result.apply(
    lambda pw: f"""#!/bin/bash
set -eux
apt-get update
apt-get install -y redis-server
sed -i 's/^bind .*/bind 0.0.0.0/' /etc/redis/redis.conf
cat >> /etc/redis/redis.conf <<'CONF'
requirepass {pw}
maxmemory 512mb
save ""
CONF
systemctl restart redis-server
"""
)

redis_vm = gcp.compute.Instance(
    "redis-vm",
    name="benchmark-redis",
    machine_type="e2-micro",
    zone=zone,
    tags=["redis"],
    boot_disk=gcp.compute.InstanceBootDiskArgs(
        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
            image="debian-cloud/debian-12", size=10, type="pd-standard"
        )
    ),
    network_interfaces=[
        gcp.compute.InstanceNetworkInterfaceArgs(
            network="default",
            # External IP only so apt can install redis; the firewall does not expose 6379 publicly.
            access_configs=[gcp.compute.InstanceNetworkInterfaceAccessConfigArgs()],
        )
    ],
    metadata_startup_script=redis_startup,
    opts=pulumi.ResourceOptions(depends_on=apis),
)

redis_url = pulumi.Output.concat(
    "redis://default:", redis_password.result, "@", redis_vm.network_interfaces[0].network_ip, ":6379"
)


def service(name: str, image: str) -> gcp.cloudrunv2.Service:
    svc = gcp.cloudrunv2.Service(
        name,
        name=name,
        location=region,
        ingress="INGRESS_TRAFFIC_ALL",
        deletion_protection=False,
        template=gcp.cloudrunv2.ServiceTemplateArgs(
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(min_instance_count=1, max_instance_count=1),
            max_instance_request_concurrency=20,
            # Direct VPC egress to reach the Redis VM's internal IP.
            vpc_access=gcp.cloudrunv2.ServiceTemplateVpcAccessArgs(
                egress="PRIVATE_RANGES_ONLY",
                network_interfaces=[
                    gcp.cloudrunv2.ServiceTemplateVpcAccessNetworkInterfaceArgs(network="default", subnetwork="default")
                ],
            ),
            containers=[
                gcp.cloudrunv2.ServiceTemplateContainerArgs(
                    image=image,
                    ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(container_port=8080),
                    envs=[gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(name="REDIS_URL", value=redis_url)],
                    resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                        limits={"cpu": "1", "memory": "512Mi"}
                    ),
                )
            ],
        ),
        opts=pulumi.ResourceOptions(depends_on=apis + [redis_vm]),
    )
    gcp.cloudrunv2.ServiceIamMember(
        f"{name}-public",
        name=svc.name,
        location=region,
        role="roles/run.invoker",
        member="allUsers",
    )
    return svc


node_svc = service("node-fastify", node_image)
rust_svc = service("rust-poem", rust_image)

# Cheapest VM: e2-micro. Installs wrk, setup.py and the bench script, pre-wired to both services
# and to the Redis VM (REDIS_URL in a root-only file; the startup script is a Pulumi secret).
scripts = Path(__file__).resolve().parent.parent / "scripts"
bench_sh = (scripts / "bench.sh").read_text()
setup_py = (scripts / "setup.py").read_text()


def render_startup(values):
    node_url, rust_url, redis = values
    return f"""#!/bin/bash
set -eux
apt-get update
apt-get install -y wrk curl python3
cat > /etc/benchmark.env <<'ENV'
NODE_URL={node_url}
RUST_URL={rust_url}
ENV
install -m 600 /dev/null /etc/benchmark-redis.env
cat > /etc/benchmark-redis.env <<'ENV'
REDIS_URL={redis}
ENV
cat > /usr/local/bin/bench.sh <<'BENCH'
{bench_sh}
BENCH
cat > /usr/local/bin/setup.py <<'SETUP'
{setup_py}
SETUP
chmod +x /usr/local/bin/bench.sh /usr/local/bin/setup.py
"""


startup = pulumi.Output.all(node_svc.uri, rust_svc.uri, redis_url).apply(render_startup)

vm = gcp.compute.Instance(
    "bench-vm",
    name="benchmark-wrk",
    machine_type="e2-micro",
    zone=zone,
    boot_disk=gcp.compute.InstanceBootDiskArgs(
        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
            image="debian-cloud/debian-12", size=10, type="pd-standard"
        )
    ),
    network_interfaces=[
        gcp.compute.InstanceNetworkInterfaceArgs(
            network="default",
            access_configs=[gcp.compute.InstanceNetworkInterfaceAccessConfigArgs()],
        )
    ],
    metadata_startup_script=startup,
    opts=pulumi.ResourceOptions(depends_on=apis),
)

pulumi.export("nodeUrl", node_svc.uri)
pulumi.export("rustUrl", rust_svc.uri)
pulumi.export("redisHost", redis_vm.network_interfaces[0].network_ip)
pulumi.export("vmName", vm.name)
pulumi.export("vmSsh", pulumi.Output.concat("gcloud compute ssh ", vm.name, " --zone ", zone))
