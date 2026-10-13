# Senaste Amazon Linux 2023 (x86_64) - inget hårdkodat AMI-id
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# Standard-VPC i regionen
data "aws_vpc" "default" {
  default = true
}

# Brandvägg: bara HTTP (80) in, allt ut
resource "aws_security_group" "web" {
  name        = "${var.ec2_name}-sg"
  description = "Allow HTTP in, all out"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
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

resource "aws_instance" "web" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = var.ec2_type
  vpc_security_group_ids      = [aws_security_group.web.id]
  associate_public_ip_address = true

  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    app_py_b64       = base64encode(file("${path.module}/../app/app.py"))
    requirements_b64 = base64encode(file("${path.module}/../app/requirements.txt"))
    gemini_api_key   = var.gemini_api_key
  })
  user_data_replace_on_change = true

  tags = {
    Name = var.ec2_name
  }
}
