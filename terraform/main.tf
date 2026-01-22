## S3 Data Lake
resource "aws_s3_bucket" "data_lake"{
  bucket  = "${var.project_name}-data-lake-bucket-2026"
  tags    = {
    name  = "${var.project_name}-data-lake"
  }
  force_destroy = true
}

## VPC & Subnet
# VPC
resource "aws_vpc" "main_vpc" {
  cidr_block  = "10.0.0.0/16"
  tags        = {
    name      = "${var.project_name}-vpc"
  }
}
# Public Subnet
resource "aws_subnet" "public_subnet" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"
  map_public_ip_on_launch = true
  tags    = {
    name  = "${var.project_name}-public-subnet"
  }
}
# Private Public
resource "aws_subnet" "private_subnet_1" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}a"
  tags    = {
    name  = "${var.project_name}-private-subnet-1"
  }
}
resource "aws_subnet" "private_subnet_2" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.0.4.0/24"
  availability_zone = "${var.aws_region}b"
  tags    = {
    name  = "${var.project_name}-private-subnet-2"
  }
}
resource "aws_subnet" "private_subnet_3" {
  vpc_id            = aws_vpc.main_vpc.id
  cidr_block        = "10.0.5.0/24"
  availability_zone = "${var.aws_region}c"
  tags    = {
    name  = "${var.project_name}-private-subnet-3"
  }
}

## Internet Gateway
resource "aws_internet_gateway" "internet_gateway" {
  vpc_id  = aws_vpc.main_vpc.id
  tags    = {
    name  = "${var.project_name}-internet_gateway"
  }
}

## Route Table
resource "aws_route_table" "public_route" {
  vpc_id    = aws_vpc.main_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.internet_gateway.id
  }
  tags    = {
    name  = "${var.project_name}-public_route"
  }
}
# Route Table connect to Public Subnet
resource "aws_route_table_association" "public_assoc" {
  subnet_id       = aws_subnet.public_subnet.id
  route_table_id  = aws_route_table.public_route.id
}

resource "aws_security_group" "airflow_security_group" {
  name = "airflow-security-group"
  description = "Allow SSH and Airflow inbound traffic"
  vpc_id = aws_vpc.main_vpc.id
  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "From Airflow"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    name = "${var.project_name}-airflow-security-group"
  }
}

resource "aws_security_group" "redshift_security_group" {
  name = "redshift-security-group"
  description = "Allow traffic from EC2 only"
  vpc_id = aws_vpc.main_vpc.id
  ingress {
    description = "SSH from anywhere"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    security_groups = [aws_security_group.airflow_security_group.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    name = "${var.project_name}-airflow-security-group"
  }
}

resource "aws_iam_role" "ec2_s3_access_role" {
  name = "admin-ec2-s3-role"
assume_role_policy = jsonencode ({
  Version = "2012-10-17"
  Statement = [{
    Action = "sts:AssumeRole"
    Effect = "Allow"
    Principal = {
      Service = "ec2.amazonaws.com"
    }
  }]
})
}

resource "aws_iam_role" "redshift_access_role" {
  name = "admin-redshift-role"
assume_role_policy = jsonencode ({
  Version = "2012-10-17"
  Statement = [{
    Action = "sts:AssumeRole"
    Effect = "Allow"
    Principal = {
      Service = "redshift.amazonaws.com"
    }
  }]
})
}


resource "aws_iam_role_policy_attachment" "s3_full_access" {
  role = aws_iam_role.ec2_s3_access_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}
resource "aws_iam_role_policy_attachment" "redshift_s3_read" {
  role       = aws_iam_role.redshift_access_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "admin-ec2-profile"
  role = aws_iam_role.ec2_s3_access_role.name
}

## EC2
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "airflow_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.small"

  subnet_id       = aws_subnet.public_subnet.id
  vpc_security_group_ids = [aws_security_group.airflow_security_group.id]
  # for ssh to server
  associate_public_ip_address = true

  key_name              = "admin-key"
  iam_instance_profile  = aws_iam_instance_profile.ec2_profile.name
  tags = {
    name = "${var.project_name}-ec2-airflow-server"
  }
}