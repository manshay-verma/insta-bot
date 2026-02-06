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

    def __init__(self, download_dir: str = "downloads", progress_callback=None,
                 organize_by_type: bool = False, organize_by_user: bool = False):
        self.download_dir = download_dir
        self.progress_callback = progress_callback
        self.organize_by_type = organize_by_type
        self.organize_by_user = organize_by_user
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            logger.info(f"Created download directory: {self.download_dir}")
        
        # Realistic User-Agent to avoid being blocked by CDNs
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _get_organized_path(self, filename: str, media_type: str = None, username: str = None) -> str:
        """
        Generate organized file path based on settings.
        
        Structure options:
        - organize_by_type only: downloads/images/, downloads/videos/, etc.
        - organize_by_user only: downloads/{username}/
        - Both: downloads/{username}/images/
        
        Args:
            filename: The filename for the download
            media_type: Type of media (images, videos, reels, stories, carousels)
            username: Optional username for user-based organization
            
        Returns:
            Full file path with organized subdirectories
        """
        path_parts = [self.download_dir]
        
        if self.organize_by_user and username:
            path_parts.append(username)
        
        if self.organize_by_type and media_type:
            path_parts.append(media_type)
        
        subdir = os.path.join(*path_parts)
        if not os.path.exists(subdir):
            os.makedirs(subdir)
            logger.info(f"Created subdirectory: {subdir}")
        
        return os.path.join(subdir, filename)

    def download_image(self, url: str, filename: str, username: str = None, progress_callback=None) -> Optional[str]:
        """
        Download a single image.
        """
        return self._download_media(url, filename, media_type="images", username=username, progress_callback=progress_callback)

    def download_video(self, url: str, filename: str, username: str = None, progress_callback=None) -> Optional[str]:
        """
        Download a single video (post or reel).
        """
        return self._download_media(url, filename, media_type="videos", username=username, progress_callback=progress_callback)

    def _download_media(self, url: str, filename: str, media_type: str = None, username: str = None, progress_callback=None) -> Optional[str]:
        """
        Generic download method with smart extension detection, resume support, and progress tracking.
        """
        try:
            # We use stream=True to check headers before downloading full content
            response = requests.get(url, stream=True, timeout=60, headers=self.headers)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').lower()
            total_size_server = int(response.headers.get('Content-Length', 0))
            
            actual_ext = os.path.splitext(filename)[1].lower()

            # Fix extension if it doesn't match content type
            if 'video' in content_type and actual_ext not in ['.mp4', '.mov', '.avi']:
                filename = os.path.splitext(filename)[0] + ".mp4"
            elif 'image' in content_type and actual_ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                filename = os.path.splitext(filename)[0] + ".jpg"
            
            # Use organized path if organization is enabled
            filepath = self._get_organized_path(filename, media_type=media_type, username=username)
            
            initial_pos = 0
            mode = 'wb'
            
            if os.path.exists(filepath):
                initial_pos = os.path.getsize(filepath)
                if total_size_server > 0 and initial_pos >= total_size_server:
                    logger.info(f"File {filename} already exists and is complete ({initial_pos}/{total_size_server} bytes). Skipping.")
                    response.close()
                    # Trigger 100% callback if complete
                    cb = progress_callback or self.progress_callback
                    if cb:
                        cb(filename, initial_pos, total_size_server)
                    return filepath
                
                if initial_pos > 0:
                    # Close the initial response and start a new one with Range header
                    response.close()
                    resume_headers = self.headers.copy()
                    resume_headers['Range'] = f"bytes={initial_pos}-"
                    
                    response = requests.get(url, stream=True, timeout=60, headers=resume_headers)
                    
                    # Check if server supports Range request (Status code 206)
                    if response.status_code == 206:
                        logger.info(f"Resuming download for {filename} from {initial_pos} bytes.")
                        mode = 'ab'
                    else:
                        logger.warning(f"Server does not support Range for {url}. Restarting download from beginning.")
                        initial_pos = 0
                        mode = 'wb'

            current_size = initial_pos
            total_size = total_size_server if total_size_server > 0 else current_size
            
            cb = progress_callback or self.progress_callback

            with open(filepath, mode) as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        current_size += len(chunk)
                        if cb:
                            cb(filename, current_size, total_size)
            
            logger.info(f"Successfully downloaded {media_type or 'media'}: {filename}")
            return filepath
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    def download_reel(self, url: str, filename: str, username: str = None, progress_callback=None) -> Optional[str]:
        """
        Download an Instagram Reel. 
        """
        logger.info(f"Downloading Reel: {filename}")
        return self._download_media(url, filename, media_type="reels", username=username, progress_callback=progress_callback)

    def download_story(self, url: str, filename: str, username: str = None, progress_callback=None) -> Optional[str]:
        """
        Download an Instagram Story.
        """
        logger.info(f"Downloading Story: {filename}")
        return self._download_media(url, filename, media_type="stories", username=username, progress_callback=progress_callback)

    def download_carousel(self, urls: List[str], base_filename: str, username: str = None, progress_callback=None) -> List[Optional[str]]:
        """
        Download all items in a carousel post.
        """
        filenames = []
        for i, url in enumerate(urls):
            # Pass a dummy filename, _download_media will fix the extension
            filenames.append(f"{base_filename}_{i+1}.item")
        
        logger.info(f"Starting carousel download for {base_filename} ({len(urls)} items)")
        return self.bulk_download(urls, filenames, username=username, media_type="carousels", progress_callback=progress_callback)

    def bulk_download(self, urls: List[str], filenames: List[str], max_workers: int = 5, username: str = None, media_type: str = None, progress_callback=None) -> List[Optional[str]]:
        """
        Download multiple files in parallel and maintain original order.
        """
        results = [None] * len(urls)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map futures to their original index to preserve order
            future_to_index = {
                executor.submit(self._download_media, url, filenames[i], media_type=media_type, username=username, progress_callback=progress_callback): i
                for i, url in enumerate(urls)
            }
            
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    logger.error(f"Bulk download failed: {e}")
                    results[index] = None
                    
        return results

    def _dispatch_download(self, url: str, filename: str) -> Optional[str]:
        """
        Helper to dispatch to correct download method.
        """
        return self._download_media(url, filename)

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
