# modules/rds/main.tf
resource "aws_db_subnet_group" "main" {
  name       = "instabot-rds-sng"
  subnet_ids = var.private_subnets

  tags = {
    Name = "instabot-rds-sng"
  }
}

resource "aws_db_instance" "postgres" {
  allocated_storage      = 20
  db_name                = "instabot_db"
  engine                 = "postgres"
  engine_version         = "15.3"
  instance_class         = "db.t3.micro"
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  skip_final_snapshot    = true
  multi_az               = false

  tags = {
    Name = "instabot-pg"
  }
}
