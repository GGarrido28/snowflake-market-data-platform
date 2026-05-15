terraform {
  backend "s3" {
    bucket       = "backend-893072528957-us-east-2-an"
    key          = "snowflake-market-data-platform/dev/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}
