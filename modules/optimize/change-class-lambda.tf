module "lambda_function2" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = var.change_class_function_name
  handler       = "change_class_lambda.lambda_handler"
  runtime       = "python3.10"
  source_path   = "./scripts/change_class_lambda.py"
  timeout       = 180
  environment_variables = {
    KEY = var.key
    VALUE = var.value
  }

  create_package = true

  # IAM
  attach_policy_statements = true
  policy_statements = {
    s3 = {
      actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:PutObjectTagging",
        "s3:GetObjectTagging"
      ]
      resources = [
        var.source_bucket_arn,
        "${var.source_bucket_arn}/*"
      ]
      effect    = "Allow"
    }
  }
}

resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda_function2.lambda_function_name
  principal     = "s3.amazonaws.com"

  source_arn = var.source_bucket_arn
}


resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = var.source_bucket_id

  lambda_function {
    lambda_function_arn = module.lambda_function2.lambda_function_arn
    events              = ["s3:ObjectTagging:Put"]
  }

  depends_on = [aws_lambda_permission.allow_bucket]
}
