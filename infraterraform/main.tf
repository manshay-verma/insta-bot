# infraterraform/main.tf
provider "aws" {
  region = var.region
}

module "vpc" {
  source   = "./modules/vpc"
  vpc_cidr = "10.0.0.0/16"
}

resource "aws_security_group" "web_sg" {
  name        = "instabot-web-sg"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

module "s3_buckets" {
  source      = "./modules/s3"
  environment = "dev"
  bucket_names = ["raw", "processed", "exports", "backups"]
}

module "rds" {
  source            = "./modules/rds"
  db_username       = "postgres"
  db_password       = var.db_password
  private_subnets  = module.vpc.private_subnets
  security_group_id = aws_security_group.web_sg.id
}

module "compute" {
  source            = "./modules/ec2"
  ami_id            = "ami-0c7217cdde317cfec" # Example Amazon Linux 2
  instance_type     = "t3.medium"
  public_subnets    = module.vpc.public_subnets
  security_group_id = aws_security_group.web_sg.id
  user_data         = file("./scripts/setup.sh")
}
