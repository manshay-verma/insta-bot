# modules/ec2/main.tf
resource "aws_launch_template" "bot" {
  name_prefix   = "instabot-bot-"
  image_id      = var.ami_id
  instance_type = var.instance_type

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [var.security_group_id]
  }

  user_data = base64encode(var.user_data)

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "instabot-bot"
    }
  }
}

resource "aws_autoscaling_group" "bot" {
  desired_capacity    = 2
  max_size            = 5
  min_size            = 1
  vpc_zone_identifier = var.public_subnets

  launch_template {
    id      = aws_launch_template.bot.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "instabot-bot-asg"
    propagate_at_launch = true
  }
}
