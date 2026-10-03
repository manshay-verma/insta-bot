# modules/s3/main.tf
resource "aws_s3_bucket" "media" {
  count  = 4
  bucket = "instabot-media-${var.environment}-${var.bucket_names[count.index]}"

  tags = {
    Name = "instabot-media-${var.bucket_names[count.index]}"
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  count  = 4
  bucket = aws_s3_bucket.media[count.index].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  count  = 4
  bucket = aws_s3_bucket.media[count.index].id

  rule {
    id     = "expire-logs"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}
