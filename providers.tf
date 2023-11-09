provider "aws" {
  region = var.region
  default_tags {
    tags = {
      "Environment" = "raziel-test"
      "Owner" = "raziel"
    }
  }
}

terraform {
  backend "s3" {
    bucket = "bucket-optimizer-ez-test-tf-backend"
    key    = "dev/terraform.tfstate"
    region = "us-east-1"
  }
}
