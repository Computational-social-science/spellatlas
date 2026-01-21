import os
import boto3
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class S3Client:
    def __init__(self):
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region_name = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "spellatlas-data")
        
        self.client = None
        if self.endpoint_url and self.aws_access_key_id and self.aws_secret_access_key:
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    region_name=self.region_name
                )
                self._ensure_bucket_exists()
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")

    def _ensure_bucket_exists(self):
        """Ensure the target bucket exists."""
        if not self.client:
            return

        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' exists.")
        except ClientError:
            # Bucket does not exist, create it
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
                logger.info(f"Bucket '{self.bucket_name}' created.")
            except Exception as e:
                logger.error(f"Failed to create bucket '{self.bucket_name}': {e}")

    def upload_file(self, file_path, object_name=None):
        """Upload a file to an S3 bucket."""
        if not self.client:
            logger.warning("S3 client not initialized. Skipping upload.")
            return False

        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            self.client.upload_file(file_path, self.bucket_name, object_name)
            logger.info(f"Uploaded {file_path} to {self.bucket_name}/{object_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False

    def download_file(self, object_name, file_path):
        """Download a file from an S3 bucket."""
        if not self.client:
            logger.warning("S3 client not initialized. Skipping download.")
            return False

        try:
            self.client.download_file(self.bucket_name, object_name, file_path)
            logger.info(f"Downloaded {self.bucket_name}/{object_name} to {file_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            return False
