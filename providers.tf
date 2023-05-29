provider "aws" {
  region = var.region
}

terraform {
  backend "s3" {
    bucket = "bucket-optimizer-ez-tf-backend"
    key    = "dev/terraform.tfstate"
    region = "eu-central-1"
  }
}
