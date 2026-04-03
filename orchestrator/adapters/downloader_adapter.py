"""
Downloader Adapter

Connects orchestrator with automation/downloader/media_downloader.py
Provides media download and S3 upload capabilities.
"""

import logging
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

from .base_adapter import BaseAdapter, AdapterType, TaskType, TaskResult

# Add automation to path
automation_path = Path(__file__).parent.parent.parent / "automation"
sys.path.insert(0, str(automation_path))

logger = logging.getLogger(__name__)


class DownloaderAdapter(BaseAdapter):
    """
    Adapter for media downloads.
    
    Wraps automation/downloader/media_downloader.py (MediaDownloader)
    
    Supported Tasks:
    - DOWNLOAD_IMAGE, DOWNLOAD_VIDEO, DOWNLOAD_CAROUSEL
    - DOWNLOAD_STORY, BULK_DOWNLOAD
    - UPLOAD_S3
    
    Usage:
        adapter = DownloaderAdapter(api_client, account_id=1)
        await adapter.initialize()
        result = await adapter.execute(
            TaskType.BULK_DOWNLOAD,
            ["https://instagram.com/p/xyz", ...],
            max_workers=5
        )
        await adapter.cleanup()
    """
    
    adapter_type = AdapterType.DOWNLOADER
    
    def __init__(
        self,
        *args,
        download_dir: str = "downloads",
        organize_by_type: bool = True,
        organize_by_user: bool = False,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.download_dir = download_dir
        self.organize_by_type = organize_by_type
        self.organize_by_user = organize_by_user
        self.downloader = None
    
    async def initialize(self) -> bool:
        """Initialize MediaDownloader."""
        try:
            from downloader.media_downloader import MediaDownloader
            
            self.downloader = MediaDownloader(
                download_dir=self.download_dir,
                organize_by_type=self.organize_by_type,
                organize_by_user=self.organize_by_user
            )
            
            self._initialized = True
            logger.info(f"Downloader initialized, saving to: {self.download_dir}")
            return True
            
        except ImportError as e:
            logger.error(f"Failed to import MediaDownloader: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Downloader: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup downloader resources."""
        self.downloader = None
        self._initialized = False
        logger.info("Downloader adapter cleaned up")
    
    def get_supported_tasks(self) -> List[TaskType]:
        """Get supported task types."""
        return [
            TaskType.DOWNLOAD_IMAGE,
            TaskType.DOWNLOAD_VIDEO,
            TaskType.DOWNLOAD_CAROUSEL,
            TaskType.DOWNLOAD_STORY,
            TaskType.BULK_DOWNLOAD,
            TaskType.UPLOAD_S3,
        ]
    
    async def execute(
        self,
        task_type: TaskType,
        targets: List[str],
        **kwargs
    ) -> TaskResult:
        """Execute a download task."""
        if not self._initialized:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=["Adapter not initialized"]
            )
        
        handlers = {
            TaskType.DOWNLOAD_IMAGE: self._download_images,
            TaskType.DOWNLOAD_VIDEO: self._download_videos,
            TaskType.DOWNLOAD_CAROUSEL: self._download_carousels,
            TaskType.DOWNLOAD_STORY: self._download_stories,
            TaskType.BULK_DOWNLOAD: self._bulk_download,
            TaskType.UPLOAD_S3: self._upload_to_s3,
        }
        
        handler = handlers.get(task_type)
        if not handler:
            return TaskResult(
                success=False,
                task_type=task_type,
                errors=[f"Unsupported task: {task_type}"]
            )
        
        # Run in executor (downloader is synchronous)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: handler(targets, **kwargs))
    
    # ==================== Task Handlers ====================
    
    def _download_images(self, targets: List[str], **kwargs) -> TaskResult:
        """Download images."""
        username = kwargs.get("username")
        success_count = 0
        errors = []
        downloaded = []
        
        for i, url in enumerate(targets):
            filename = kwargs.get("filename", f"image_{i+1}")
            try:
                filepath = self.downloader.download_image(url, filename, username=username)
                if filepath:
                    success_count += 1
                    downloaded.append(filepath)
                    if self.callback:
                        self.callback.on_download(url, "image", filepath, True)
            except Exception as e:
                errors.append(str(e))
                if self.callback:
                    self.callback.on_download(url, "image", None, False, error_message=str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.DOWNLOAD_IMAGE,
            data={"files": downloaded},
            items_processed=success_count,
            errors=errors
        )
    
    def _download_videos(self, targets: List[str], **kwargs) -> TaskResult:
        """Download videos."""
        username = kwargs.get("username")
        success_count = 0
        errors = []
        downloaded = []
        
        for i, url in enumerate(targets):
            filename = kwargs.get("filename", f"video_{i+1}")
            try:
                filepath = self.downloader.download_video(url, filename, username=username)
                if filepath:
                    success_count += 1
                    downloaded.append(filepath)
                    if self.callback:
                        self.callback.on_download(url, "video", filepath, True)
            except Exception as e:
                errors.append(str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.DOWNLOAD_VIDEO,
            data={"files": downloaded},
            items_processed=success_count,
            errors=errors
        )
    
    def _download_carousels(self, targets: List[str], **kwargs) -> TaskResult:
        """Download carousel posts."""
        username = kwargs.get("username")
        success_count = 0
        errors = []
        downloaded = []
        
        # Targets should be list of URL lists for carousels
        for i, urls in enumerate(targets):
            if isinstance(urls, str):
                urls = [urls]
            
            base_filename = kwargs.get("filename", f"carousel_{i+1}")
            try:
                filepaths = self.downloader.download_carousel(urls, base_filename, username=username)
                if filepaths:
                    success_count += 1
                    downloaded.extend(filepaths)
            except Exception as e:
                errors.append(str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.DOWNLOAD_CAROUSEL,
            data={"files": downloaded},
            items_processed=success_count,
            errors=errors
        )
    
    def _download_stories(self, targets: List[str], **kwargs) -> TaskResult:
        """Download stories."""
        username = kwargs.get("username")
        success_count = 0
        errors = []
        downloaded = []
        
        for i, url in enumerate(targets):
            filename = kwargs.get("filename", f"story_{i+1}")
            try:
                filepath = self.downloader.download_story(url, filename, username=username)
                if filepath:
                    success_count += 1
                    downloaded.append(filepath)
            except Exception as e:
                errors.append(str(e))
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.DOWNLOAD_STORY,
            data={"files": downloaded},
            items_processed=success_count,
            errors=errors
        )
    
    def _bulk_download(self, targets: List[str], **kwargs) -> TaskResult:
        """Bulk parallel download."""
        max_workers = kwargs.get("max_workers", 5)
        username = kwargs.get("username")
        media_type = kwargs.get("media_type")
        
        # Generate filenames
        filenames = [f"media_{i+1}" for i in range(len(targets))]
        
        try:
            results = self.downloader.bulk_download(
                urls=targets,
                filenames=filenames,
                max_workers=max_workers,
                username=username,
                media_type=media_type
            )
            
            success_count = len([r for r in results if r])
            
            # Log each download
            if self.callback:
                for url, result in zip(targets, results):
                    self.callback.on_download(
                        target_url=url,
                        media_type=media_type or "media",
                        file_path=result,
                        success=bool(result)
                    )
            
            return TaskResult(
                success=success_count > 0,
                task_type=TaskType.BULK_DOWNLOAD,
                data={"files": results, "success_count": success_count},
                items_processed=success_count
            )
            
        except Exception as e:
            return TaskResult(
                success=False,
                task_type=TaskType.BULK_DOWNLOAD,
                errors=[str(e)]
            )
    
    def _upload_to_s3(self, targets: List[str], **kwargs) -> TaskResult:
        """Upload files to S3."""
        bucket_name = kwargs.get("bucket_name")
        if not bucket_name:
            return TaskResult(
                success=False,
                task_type=TaskType.UPLOAD_S3,
                errors=["bucket_name is required"]
            )
        
        success_count = 0
        errors = []
        uploaded = []
        
        for filepath in targets:
            try:
                object_name = kwargs.get("object_name")
                result = self.downloader.upload_to_s3(filepath, bucket_name, object_name)
                if result:
                    success_count += 1
                    uploaded.append(filepath)
            except Exception as e:
                errors.append(f"{filepath}: {str(e)}")
        
        return TaskResult(
            success=success_count > 0,
            task_type=TaskType.UPLOAD_S3,
            data={"uploaded": uploaded},
            items_processed=success_count,
            errors=errors
        )
