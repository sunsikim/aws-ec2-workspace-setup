from typing import List


def create_vpc(ec2_client, vpc_name: str, vpc_cidr: str):
    """
    Create VPC whose value for name tag is vpc_name and covers IP range defined as vpc_cidr(subnet mask: 255.255.0.0).
    Region and account credential is predefined by ec2_client.
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC to be created
    :param vpc_cidr: CIDR notation of IP range with subnet mask 255.255.0.0
    :return: None
    """
    ec2_client.create_vpc(
        CidrBlock=vpc_cidr,
        TagSpecifications=[
            {
                "ResourceType": "vpc",
                "Tags": [{"Key": "Name", "Value": vpc_name}]
            }
        ]
    )


def create_vpc_security_group(
        ec2_client,
        vpc_name: str,
        ingress_ports: List[str],
):
    """
    Create default security group within VPC and authorize connections to ingress ports
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC to create security group
    :param ingress_ports: list of port(ex. '22') or range of ports(ex. '8888-8890')
    :return: ID of security group
    """
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    response = ec2_client.create_security_group(
        GroupName=f"{vpc_name.replace('_', '-')}-sg",
        Description="traffic rules over EC2 workspace",
        VpcId=vpc_id,
    )
    sg_id = response["GroupId"]
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=_parse_ip_permissions(ingress_ports)
    )


def create_vpc_internet_gateway(ec2_client, vpc_name: str):
    """
    Create internet gateway and attach it to a VPC
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC to attach created internet gateway
    :return: None
    """
    igw_id = ec2_client.create_internet_gateway(
        TagSpecifications=[
            {
                "ResourceType": "internet-gateway",
                "Tags": [{"Key": "Name", "Value": f"{vpc_name.replace('_', '-')}-igw"}]
            }
        ]
    )["InternetGateway"]["InternetGatewayId"]
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    ec2_client.attach_internet_gateway(
        InternetGatewayId=igw_id, VpcId=vpc_id
    )


def create_subnet(
        ec2_client,
        vpc_name: str,
        subnet_name: str,
        cidr_substitute: str,
        region_name: str,
        az_postfix: str,
):
    """
    Create a subnet within a VPC
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC to create subnet
    :param subnet_name: name of subnet to be created
    :param cidr_substitute: integer between 5 and 254 to be used as substitute for 0 of CIDR block
    :param region_name: name of region
    :param az_postfix: one of ('a', 'b', 'c', 'd') used to specify availability zone within current region
    :return: None
    """
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    vpc_info = ec2_client.describe_vpcs(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
    )["Vpcs"][0]
    subnet_cidr = vpc_info["CidrBlock"].split(".")[:-1]  # ex. '172.50.0.0/16' -> ['172', '50', '0']
    subnet_cidr[2] = cidr_substitute  # ex. ['172', '50', '0'] -> ['172', '50', '100']
    subnet_cidr = f"{'.'.join(subnet_cidr)}.0/24"  # ex. ['172', '50', '100'] -> '172.50.100.0/24'
    ec2_client.create_subnet(
        CidrBlock=subnet_cidr,
        VpcId=vpc_id,
        AvailabilityZone=f"{region_name}{az_postfix}",
        TagSpecifications=[
            {
                "ResourceType": "subnet",
                "Tags": [{"Key": "Name", "Value": subnet_name}]
            }
        ]
    )


def create_route_table(
        ec2_client,
        vpc_name: str,
        rt_name: str,
        is_public: bool,
):
    """
    Create basic route table that allows traffic from VPC. If `is_public` is set to True, add route to internet gateway
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC to create route table
    :param rt_name: name of route table to be created
    :param is_public: whether route to VPC internet gateway has to be added in the table
    :return: None
    """
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    response = ec2_client.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "route-table",
                "Tags": [{"Key": "Name", "Value": rt_name}]
            }
        ]
    )
    if is_public:
        igw_info = ec2_client.describe_internet_gateways(
            Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
        )["InternetGateways"]
        assert len(igw_info) > 0, f"Internet gateway attached to VPC '{vpc_name}' is not generated"
        ec2_client.create_route(
            DestinationCidrBlock="0.0.0.0/0",
            GatewayId=igw_info[0]["InternetGatewayId"],
            RouteTableId=response["RouteTable"]["RouteTableId"],
        )


def create_route_table_subnet_association(
        ec2_client,
        vpc_name: str,
        subnet_name: str,
        rt_name: str,
):
    """
    Associate created route table to created subnet
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC where route table is created
    :param subnet_name: name of subnet
    :param rt_name: name of route table
    :return:
    """
    subnet_id = fetch_subnet_id(ec2_client, vpc_name, subnet_name)
    rt_id = ec2_client.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [fetch_vpc_id(ec2_client, vpc_name)]},
            {"Name": "tag:Name", "Values": [rt_name]}
        ]
    )["RouteTables"][0]["RouteTableId"]
    ec2_client.associate_route_table(RouteTableId=rt_id, SubnetId=subnet_id)


def fetch_vpc_id(ec2_client, vpc_name: str) -> str:
    """
    This project assigns unique name to unique VPC, so normal response should contain only one set of VPC information.
    If list is empty, it means that VPC is not created. If there are multiple VPCs with given name, it must be that
    one of VPCs is created from outside of this project.
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC to fetch corresponding ID
    :return: VpcId
    """
    vpc_info = ec2_client.describe_vpcs(
        Filters=[{"Name": "tag:Name", "Values": [vpc_name]}]
    )["Vpcs"]
    if len(vpc_info) == 1:
        return vpc_info[0]["VpcId"]
    elif len(vpc_info) == 0:
        raise ValueError(f"VPC with name '{vpc_name}' does not exists")
    else:
        raise ValueError(f"VPC whose name tag value is '{vpc_name}' is ambiguous")


def fetch_vpc_security_group_id(ec2_client, vpc_name: str) -> str:
    """
    One-to-one correspondence between security group and sg_name is checked as explained in `fetch_vpc_id` method.
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC for the security group
    :return: GroupId
    """
    sg_name = f"{vpc_name.replace('_', '-')}-sg"
    sg_info = ec2_client.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [fetch_vpc_id(ec2_client, vpc_name)]},
            {"Name": "group-name", "Values": [sg_name]},
        ]
    )["SecurityGroups"]
    if len(sg_info) == 1:
        return sg_info[0]["GroupId"]
    elif len(sg_info) == 0:
        raise ValueError(f"Security group with GroupName '{sg_name}' does not exists")
    else:
        raise ValueError(f"Security group with GroupName '{sg_name}' is ambiguous")


def fetch_subnet_id(ec2_client, vpc_name: str, subnet_name: str) -> str:
    """
    One-to-one correspondence between subnet and subnet_name is checked as explained in `fetch_vpc_id` method.
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC that subnet is defined
    :param subnet_name: name of subnet to fetch ID
    :return: SubnetId
    """
    subnet_info = ec2_client.describe_subnets(
        Filters=[
            {"Name": "vpc-id", "Values": [fetch_vpc_id(ec2_client, vpc_name)]},
            {"Name": "tag:Name", "Values": [subnet_name]}
        ]
    )["Subnets"]
    if len(subnet_info) == 1:
        return subnet_info[0]["SubnetId"]
    elif len(subnet_info) == 0:
        raise ValueError(f"Subnet with name '{subnet_name}' does not exists")
    else:
        raise ValueError(f"Subnet whose name tag value is '{subnet_name}' is ambiguous")


def delete_route_table_subnet_association(
        ec2_client,
        vpc_name: str,
        subnet_name: str,
        rt_name: str,
):
    """
    Delete association between route table and subnet
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC where route table and subnet are defined
    :param subnet_name: name of subnet
    :param rt_name: name of route table
    :return: None
    """
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    associated_subnet_id = fetch_subnet_id(ec2_client, vpc_name, subnet_name)
    rt_info = ec2_client.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "association.subnet-id", "Values": [associated_subnet_id]},
            {"Name": "tag:Name", "Values": [rt_name]},
        ]
    )["RouteTables"][0]
    ec2_client.disassociate_route_table(
        AssociationId=rt_info["Associations"][0]["RouteTableAssociationId"]
    )


def delete_route_table(ec2_client, vpc_name: str, rt_name: str):
    """
    Delete route table from VPC
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC where route table is defined
    :param rt_name: name of route table to delete
    :return: None
    """
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    rt_info = ec2_client.describe_route_tables(
        Filters=[
            {"Name": "vpc-id", "Values": [vpc_id]},
            {"Name": "tag:Name", "Values": [rt_name]},
        ]
    )["RouteTables"][0]
    ec2_client.delete_route_table(RouteTableId=rt_info["RouteTableId"])


def delete_subnet(ec2_client, vpc_name: str, subnet_name: str):
    """
    Delete subnet from VPC
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC where subnet is defined
    :param subnet_name: name of subnet to delete
    :return: None
    """
    subnet_id = fetch_subnet_id(ec2_client, vpc_name, subnet_name)
    ec2_client.delete_subnet(SubnetId=subnet_id)


def delete_vpc_security_group(ec2_client, vpc_name: str):
    """
    Delete default security group of VPC
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC where security group is defined
    :return: None
    """
    security_group_id = fetch_vpc_security_group_id(ec2_client, vpc_name)
    ec2_client.delete_security_group(GroupId=security_group_id)


def delete_vpc_internet_gateway(ec2_client, vpc_name: str):
    """
    Detach internet gateway of given VPC and delete it consecutively
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC where internet gateway was defined
    :return: None
    """
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    igw_info = ec2_client.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc_id]}]
    )["InternetGateways"]
    igw_id = igw_info[0]["InternetGatewayId"]
    ec2_client.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)


def delete_vpc(ec2_client, vpc_name: str):
    """
    Delete VPC whose tagged name is vpc_name
    :param ec2_client: EC2 client created by boto3 session
    :param vpc_name: name of VPC to delete
    :return: None
    """
    vpc_id = fetch_vpc_id(ec2_client, vpc_name)
    ec2_client.delete_vpc(VpcId=vpc_id)


def _parse_ip_permissions(ingress_ports: List[str]):
    """
    Parse ingress port and convert it into port ingress permission statement. If ingress port string is:
        * single integer, both FromPort and ToPort
        * string that contains hyphen between two integers,
        * otherwise, return error since the value is not in expected format
    :param ingress_ports: list of port(ex. '22') or range of ports(ex. '8888-8890')
    :return: list of parsed permissions
    """
    permission_statements = []
    for ingress_port in ingress_ports:
        try:
            from_port = int(ingress_port)
            to_port = int(ingress_port)
        except ValueError:  # ValueError with message 'invalid literal for int() with base 10'
            if "-" in ingress_port:
                from_port, to_port = map(int, ingress_port.split("-"))
            else:
                raise ValueError(
                    f"ingress_port should be either integer or contains '-' as separator; got {ingress_port}"
                )
        if from_port == to_port:
            description = f"allow any connection attempt on port {from_port}"
        else:
            description = f"allow any connection attempt on port {from_port} to {to_port} (inclusive)"
        parsed_permission = {
            "FromPort": from_port,
            "ToPort": to_port,
            "IpProtocol": "tcp",
            "IpRanges": [
                {
                    "CidrIp": "0.0.0.0/0",
                    "Description": description
                }
            ]
        }
        permission_statements.append(parsed_permission)
    return permission_statements
