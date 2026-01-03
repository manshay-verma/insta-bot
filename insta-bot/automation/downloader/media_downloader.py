import os
import requests
import concurrent.futures
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MediaDownloader:
    """
    Production-grade media downloader for Instagram.
    Handles images, videos (reels), and carousel items.
    """

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            logger.info(f"Created download directory: {self.download_dir}")

    def download_image(self, url: str, filename: str) -> Optional[str]:
        """
        Download a single image.
        """
        try:
            filepath = os.path.join(self.download_dir, filename)
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded image: {filename}")
            return filepath
        except Exception as e:
            logger.error(f"Error downloading image {url}: {e}")
            return None

    def download_video(self, url: str, filename: str) -> Optional[str]:
        """
        Download a single video (post or reel).
        Note: For production, you might want to use a more specialized tool 
        like yt-dlp if the direct URL is not available.
        """
        try:
            filepath = os.path.join(self.download_dir, filename)
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded video: {filename}")
            return filepath
        except Exception as e:
            logger.error(f"Error downloading video {url}: {e}")
            return None

    def bulk_download(self, urls: List[str], filenames: List[str], max_workers: int = 5) -> List[Optional[str]]:
        """
        Download multiple files in parallel.
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a dictionary to map futures to filenames for tracking
            future_to_file = {
                executor.submit(self._dispatch_download, url, filenames[i]): filenames[i]
                for i, url in enumerate(urls)
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error(f"Bulk download failed for a file: {e}")
                    results.append(None)
                    
        return results

    def _dispatch_download(self, url: str, filename: str) -> Optional[str]:
        """
        Helper to dispatch to correct download method based on extension.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            return self.download_image(url, filename)
        elif ext in ['.mp4', '.mov', '.avi']:
            return self.download_video(url, filename)
        else:
            # Default to image if unknown, or handle appropriately
            return self.download_image(url, filename)

    def upload_to_s3(self, filepath: str, bucket_name: str, object_name: Optional[str] = None):
        """
        Uploads a file to an S3 bucket.
        Requires boto3 and AWS credentials.
        """
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError

            s3_client = boto3.client('s3')
            if object_name is None:
                object_name = os.path.basename(filepath)

            s3_client.upload_file(filepath, bucket_name, object_name)
            logger.info(f"Successfully uploaded {filepath} to S3 bucket {bucket_name}")
            return True
        except ImportError:
            logger.warning("boto3 not installed. S3 upload skipped.")
            return False
        except NoCredentialsError:
            logger.error("AWS credentials not found.")
            return False
        except Exception as e:
            logger.error(f"S3 upload error: {e}")
            return False
