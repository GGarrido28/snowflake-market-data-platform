terraform {
  backend "s3" {
    bucket       = "snowflake-kalshi-terraform-state-893072528957"
    key          = "snowflake-market-data-platform/dev/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}
