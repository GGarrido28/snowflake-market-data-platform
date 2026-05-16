# Kalshi Secrets Manager Setup

Kalshi API requests require two values:

- API key id
- RSA private key PEM used to sign request headers

Local development can still use the existing `.env` flow:

```text
KALSHI_API_KEY_ID=...
KALSHI_API_KEY=C:\path\to\kalshi-private-key.pem
```

AWS-deployed ingestion should use AWS Secrets Manager instead so private key
material is not stored in the Lambda image, Terraform files, or source control.

## Secret Shape

Create one JSON secret with this shape:

```json
{
  "kalshi_api_key_id": "...",
  "kalshi_private_key_pem": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
}
```

Do not commit the JSON file used to create the secret.

## Create The Secret

Use a local scratch file outside the repo or a secure shell workflow:

```powershell
aws secretsmanager create-secret `
  --name snowflake-kalshi/dev/kalshi-api `
  --secret-string file://C:\secure\kalshi-secret.json `
  --region us-east-2
```

For deployed code, set one of:

```text
KALSHI_SECRET_ARN=arn:aws:secretsmanager:...
KALSHI_SECRET_NAME=snowflake-kalshi/dev/kalshi-api
```

`KALSHI_SECRET_ARN` is preferred in AWS because IAM permissions should be
scoped to the exact secret ARN.

## Terraform

Set `kalshi_api_secret_arn` in `infra/terraform/terraform.tfvars`:

```hcl
kalshi_api_secret_arn = "arn:aws:secretsmanager:us-east-2:123456789012:secret:snowflake-kalshi/dev/kalshi-api-AbCdEf"
```

When this value is set, Terraform creates a least-privilege IAM policy that
allows `secretsmanager:GetSecretValue` only for that secret. The future Kalshi
ingestion Lambda role should attach the policy output by:

```powershell
terraform -chdir=infra/terraform output -raw kalshi_api_secret_read_policy_arn
```

The current MLB Teams Lambda is intentionally not granted Kalshi secret access.

## Runtime Behavior

The Kalshi authentication helper checks credentials in this order:

1. `KALSHI_SECRET_ARN`
2. `KALSHI_SECRET_NAME`
3. Local fallback: `KALSHI_API_KEY_ID` and `KALSHI_API_KEY`

Secrets Manager values are cached for the lifetime of the Python process so one
scraper run does not repeatedly call `GetSecretValue`.

## Live Smoke Test

The normal authentication tests mock AWS so CI does not need real credentials.
After creating the secret, run this opt-in smoke test from a machine/profile that
can call `secretsmanager:GetSecretValue`:

```powershell
$env:AWS_PROFILE = "your-aws-profile"
$env:AWS_DEFAULT_REGION = "us-east-2"
$env:KALSHI_SECRET_ARN = "arn:aws:secretsmanager:us-east-2:123456789012:secret:snowflake-kalshi/dev/kalshi-api-AbCdEf"
$env:RUN_KALSHI_SECRET_SMOKE_TEST = "1"

C:\Users\gabri\anaconda3\envs\snowflake-kalshi\python.exe -m pytest -p no:cacheprovider tests\kalshi\test_authentication_smoke.py
```

The test fetches the real secret, parses the key id, loads the RSA private key,
and signs a throwaway message. It does not print the secret value.
