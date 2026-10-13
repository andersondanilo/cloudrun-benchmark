from pathlib import Path

import pulumi
import pulumi_gcp as gcp

gcp_cfg = pulumi.Config("gcp")
cfg = pulumi.Config()
region = gcp_cfg.require("region")  # southamerica-east1 (Sao Paulo)
zone = gcp_cfg.require("zone")
node_image = cfg.require("nodeImage")
rust_image = cfg.require("rustImage")
redis_url = cfg.require_secret("redisUrl")  # Upstash, e.g. rediss://default:<pw>@<host>:6379

apis = [
    gcp.projects.Service(f"api-{s}", service=f"{s}.googleapis.com", disable_on_destroy=False)
    for s in ("run", "compute", "artifactregistry")
]


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
        opts=pulumi.ResourceOptions(depends_on=apis),
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

# Cheapest VM: e2-micro. Installs wrk, setup.py and the bench script, pre-wired to both services.
scripts = Path(__file__).resolve().parent.parent / "scripts"
bench_sh = (scripts / "bench.sh").read_text()
setup_py = (scripts / "setup.py").read_text()


def render_startup(urls):
    node_url, rust_url = urls
    return f"""#!/bin/bash
set -eux
apt-get update
apt-get install -y wrk curl python3
cat > /etc/benchmark.env <<'ENV'
NODE_URL={node_url}
RUST_URL={rust_url}
ENV
cat > /usr/local/bin/bench.sh <<'BENCH'
{bench_sh}
BENCH
cat > /usr/local/bin/setup.py <<'SETUP'
{setup_py}
SETUP
chmod +x /usr/local/bin/bench.sh /usr/local/bin/setup.py
"""


startup = pulumi.Output.all(node_svc.uri, rust_svc.uri).apply(render_startup)

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
pulumi.export("vmName", vm.name)
pulumi.export("vmSsh", pulumi.Output.concat("gcloud compute ssh ", vm.name, " --zone ", zone))
