provider "aws" {
  region = "us-west-2"
}

resource "aws_instance" "app" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "SetAnubis"
  }

  user_data = <<-EOF
              #!/bin/bash
              docker-compose -f /path/to/docker-compose.yml up -d
              EOF
}
