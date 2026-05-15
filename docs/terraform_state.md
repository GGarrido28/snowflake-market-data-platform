# Terraform State

Terraform configuration is tracked in Git. Terraform state is operational metadata that maps those resource addresses to real AWS resource IDs and provider-computed values.

This repo stores Terraform state in S3:

```text
bucket: snowflake-kalshi-terraform-state-893072528957
key:    snowflake-market-data-platform/dev/terraform.tfstate
region: us-east-2
lock:   S3 native lock file
```

## One-Time Bootstrap

The backend bucket must exist before Terraform can initialize the backend. Create or repair the bucket settings with:

```powershell
aws sso login --profile ggarrido
.\scripts\bootstrap_terraform_state.ps1 -Profile ggarrido -Region us-east-2
```

The script creates the bucket when needed, blocks public access, enables versioning, and enables default S3 encryption.

## Migrate Local State

After the backend bucket exists, migrate the current local state into S3:

```powershell
terraform -chdir=infra/terraform init -migrate-state
```

When Terraform asks whether to copy the existing state to the new backend, answer `yes`.

Then verify that state, configuration, and AWS agree:

```powershell
$LambdaImageUri = (terraform -chdir=infra/terraform output -raw lambda_image_uri).Trim()
$LambdaImageTag = $LambdaImageUri.Split(":")[-1]
terraform -chdir=infra/terraform plan -var "lambda_image_tag=$LambdaImageTag"
```

The expected result after migration is:

```text
No changes. Your infrastructure matches the configuration.
```

## Normal Workflow

After migration, use the usual Terraform loop:

```powershell
$LambdaImageUri = (terraform -chdir=infra/terraform output -raw lambda_image_uri).Trim()
$LambdaImageTag = $LambdaImageUri.Split(":")[-1]

terraform -chdir=infra/terraform plan -out=plan.tfplan -var "lambda_image_tag=$LambdaImageTag"
terraform -chdir=infra/terraform show -no-color plan.tfplan
terraform -chdir=infra/terraform apply plan.tfplan
terraform -chdir=infra/terraform plan -var "lambda_image_tag=$LambdaImageTag"
```

The final plan should report no changes. Keep passing the existing image tag unless you are intentionally deploying a new Lambda image. Commit Terraform configuration changes to Git, but do not commit state files or plan files.
