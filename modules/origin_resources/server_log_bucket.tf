resource "aws_s3_bucket" "log_bucket" {
  bucket = var.log_bucket_name
}


resource "aws_s3_bucket_policy" "allow_logging_from_another_bucket" {
  bucket = aws_s3_bucket.log_bucket.id
  policy = data.aws_iam_policy_document.allow_logging_from_another_bucket.json
}

data "aws_iam_policy_document" "allow_logging_from_another_bucket" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["logging.s3.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"

      values = [
        "arn:aws:s3:::${var.source_bucket}"
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"

      values = [
        var.aws_account_id
      ]
    }

    actions = [
      "s3:PutObject"
    ]

    resources = [
      "arn:aws:s3:::${aws_s3_bucket.log_bucket.name}/*"
    ]
  }
}

# resource "aws_s3_bucket_acl" "log_bucket_acl" {
#   bucket = aws_s3_bucket.log_bucket.id
#   acl    = var.log_bucket_acl
# }

resource "aws_s3_bucket_logging" "source_bucket_logging" {
  bucket = var.source_bucket_id

  target_bucket = aws_s3_bucket.log_bucket.id
  target_prefix = var.target_prefix
}