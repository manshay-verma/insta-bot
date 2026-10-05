import os
import boto3
from celery import shared_task
from django.conf import settings
from .models import Download

@shared_task(bind=True)
def upload_media_to_s3(self, download_id, local_file_path, s3_key=None):
    """
    Background worker that offloads large media files to AWS S3,
    protecting the backend's main thread.
    """
    try:
        download = Download.objects.get(id=download_id)
        download.status = 'uploading'
        download.save()
        
        # Configure AWS boto3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME
        )
        
        # Default key if not provided
        if not s3_key:
            filename = os.path.basename(local_file_path)
            s3_key = f"media/{download.media_type}/{filename}"
            
        print(f"Uploading {local_file_path} to {settings.AWS_STORAGE_BUCKET_NAME}/{s3_key}")
        
        s3_client.upload_file(
            local_file_path, 
            settings.AWS_STORAGE_BUCKET_NAME, 
            s3_key
        )
        
        # Finalize record
        download.s3_key = s3_key
        download.status = 'completed'
        download.save()
        
        return {"status": "success", "s3_key": s3_key}
        
    except Exception as e:
        if 'download' in locals():
            download.status = 'failed'
            download.save()
        print(f"S3 Upload failed: {str(e)}")
        raise e
