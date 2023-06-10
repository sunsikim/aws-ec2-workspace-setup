# aws-ec2-workspace-setup

I was self studying Tensorflow implementation pattern of BERT-family models, but my workstation had to be changed from x86 Intel mac to M2 mac. Tensorflow worked fine, but dependencies like [tensorflow-text](https://www.tensorflow.org/text) didn't work so fluently as in x86. So rather than putting effort on making everything work on the new machine, I decided to create another AWS EC2 workspace with x86 architecture. Code implemented in this repository contains boto3 code snippets which can be used to EC2 workspace from scratch.

## Environment

Execution environment setup

```shell
python3 --version  # Python 3.10.10
python3 -m venv venv
source venv/bin/activate
pip3 install typer==0.9.0 boto3==1.26.140
```

## Commands

Following command examples demonstrates how to configure resources required to launch EC2 workspace and delete them when unused to prevent unnecessary expenditure. All commands assume that user had created administrator IAM user(ex. `admin.kim`) as instructed in [official guide](https://docs.aws.amazon.com/IAM/latest/UserGuide/getting-set-up.html#create-an-admin).

### VPC

Codes in this repository assumes that user creates VPC with subnet mask 255.255.0.0 and subnet with subnet mask 255.255.255.0 within that VPC. Corresponding VPC cidr has to be decided by admin user. To authorize ingress traffic toward port(or range of ports) of an instance, specify them as `ports` argument parameter.

```shell
python main.py vpc create \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --vpc-name workspace \
  --vpc-cidr 172.40.0.0/16 \
  --ports 22,80,5000-5005,8888-8890
```

Note that subnet resources related to VPC must be deleted in advance to delete it. After that, execute following command to delete VPC. 

```shell
python main.py vpc delete \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --vpc-name workspace
```

### subnet

To create public subnet whose route table contains route to internet gateway and assigns public IP to launched instance, use `is-public` flag. Integer value specified as `cidr-substitute` parameter is used to define subnet CIDR with subnet mask 255.255.255.0. For example, if VPC CIDR was 172.40.0.0/16, setting CIDR substitute value to 11 defines subnet whose CIDR is 172.40.11.0/24. 

```shell
python main.py subnet create \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --vpc-name workspace \
  --subnet-name pub-a \
  --cidr-substitute 11 \
  --az-postfix a \
  --route-table-name rt-pub \
  --is-public
```

Change `is-public` flag to `no-is-public` when private subnet has to be created.  

```shell
python main.py subnet create \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --vpc-name workspace \
  --subnet-name prv-b \
  --cidr-substitute 21 \
  --az-postfix b \
  --route-table-name rt-prv \
  --no-is-public
```

In this project, a route table is assigned to single subnet. Therefore, when deleting subnet from VPC, corresponding route table is deleted as well. 

```shell
python main.py subnet delete \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --vpc-name workspace \
  --subnet-name pub-a \
  --route-table-name rt-pub
```

### Key pair

This command creates key pair to authorize SSH connection to launched instance.  

```shell
python main.py key-pair create \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --key-name workspace
```

To delete key pair, execute following command.

```shell
python main.py key-pair delete \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --key-name workspace
```

### EC2 instance

EC2 instance can be launched after all these resources are prepared. Subnet to locate created instance and key pair name to access to EC2 instance has to be specified as parameter. Then, select AMI ID and instance type from corresponding catalog in AWS EC2 console, and pass them into `image-id`, `instance-type` argument parameter respectively. 

```shell
python main.py instance run \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --vpc-name workspace \
  --subnet-name pub-a \
  --key-name workspace \
  --instance-name workspace-ubuntu \
  --image-id ami-04341a215040f91bb \
  --instance-type t2.medium
```

To stop, start, reboot, terminate instance, use following command template.

```shell
python main.py instance [stop|start|reboot|terminate] \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --vpc-name workspace \
  --subnet-name pub-a \
  --instance-name workspace-ubuntu
```

### Elastic IP(optional)

Since public IP of instance is newly created as instance gets launched or started after being stopped, it becomes hassle to manage access information of created EC2 workspace. To remove this burden, IP address for workspace has to be fixed, and elastic IP is right choice for this purpose. First, to create new elastic IP, allocate it in specified region.     

```shell
python main.py elastic-ip allocate \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --eip-name workspace-ip
```

Then, associate allocated elastic IP to workspace instance.

```shell
python main.py elastic-ip associate \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --eip-name workspace-ip \
  --instance-name workspace-ubuntu 
```

Then, fetch its information using fetch command to parse elastic IP address as associated public host address.

```shell
python main.py elastic-ip fetch \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --eip-name workspace-ip
```

To disassociate it from assigned instance or release allocated elastic IP, use following command template.

```shell
python main.py elastic-ip [disassociate|release] \
  --profile-name admin.kim \
  --region-name ap-northeast-2 \
  --eip-name workspace-ip
```
