import boto3
import commands
import pathlib
import typer

app = typer.Typer()


@app.command("configure-vpc")
def configure_vpc(
        profile_name: str = typer.Option(...),
        region_name: str = typer.Option(...),
        vpc_name: str = typer.Option(...),
        vpc_cidr: str = typer.Option(...),
        ports: str = typer.Option(...),
):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    ec2_client = session.client("ec2")
    commands.vpc.create_vpc(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        vpc_cidr=vpc_cidr,
    )
    commands.vpc.create_vpc_security_group(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        ingress_ports=ports.split(","),
    )
    commands.vpc.create_vpc_internet_gateway(ec2_client=ec2_client, vpc_name=vpc_name)


@app.command("configure-subnet")
def configure_subnet(
        profile_name: str = typer.Option(...),
        region_name: str = typer.Option(...),
        vpc_name: str = typer.Option(...),
        subnet_name: str = typer.Option(...),
        cidr_substitute: str = typer.Option(...),
        az_postfix: str = typer.Option(...),
        route_table_name: str = typer.Option(...),
        is_public: bool = typer.Option(...),
):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    ec2_client = session.client("ec2")
    commands.vpc.create_subnet(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        subnet_name=subnet_name,
        cidr_substitute=cidr_substitute,
        region_name=region_name,
        az_postfix=az_postfix,
    )
    commands.vpc.create_route_table(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        rt_name=route_table_name,
        is_public=is_public,
    )
    commands.vpc.create_route_table_subnet_association(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        subnet_name=subnet_name,
        rt_name=route_table_name,
    )


@app.command("remove-vpc")
def remove_vpc(
        profile_name: str = typer.Option(...),
        region_name: str = typer.Option(...),
        vpc_name: str = typer.Option(...),
):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    ec2_client = session.client("ec2")
    commands.vpc.delete_vpc_security_group(ec2_client=ec2_client, vpc_name=vpc_name)
    commands.vpc.delete_vpc_internet_gateway(ec2_client=ec2_client, vpc_name=vpc_name)
    commands.vpc.delete_vpc(ec2_client=ec2_client, vpc_name=vpc_name)


@app.command("remove-subnet")
def remove_subnet(
        profile_name: str = typer.Option(...),
        region_name: str = typer.Option(...),
        vpc_name: str = typer.Option(...),
        subnet_name: str = typer.Option(...),
        route_table_name: str = typer.Option(...),
):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    ec2_client = session.client("ec2")
    commands.vpc.delete_route_table_subnet_association(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        subnet_name=subnet_name,
        rt_name=route_table_name,
    )
    commands.vpc.delete_route_table(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        rt_name=route_table_name,
    )
    commands.vpc.delete_subnet(
        ec2_client=ec2_client,
        vpc_name=vpc_name,
        subnet_name=subnet_name,
    )


if __name__ == "__main__":
    app()
