# Implementation Plan - Media Downloader Module

This plan outlines the implementation of the `MediaDownloader` class, which will handle downloading various types of media from Instagram.

## Proposed Changes

### Automation Component

#### [NEW] [media_downloader.py](file:///e:/TempFolder/Desktop_21_07_2025/Python/InstBot/insta-bot/automation/downloader/media_downloader.py)
- Implement `MediaDownloader` class.
- Methods:
    - `download_image(url, filename)`: Downloads a single image using `requests`.
    - `download_video(url, filename)`: Downloads a video.
    - `download_reel(url, filename)`: Downloads a reel.
    - `bulk_download(urls, parallel)`: Downloads multiple URLs in parallel using `ThreadPoolExecutor`.
    - `upload_to_s3(filepath, bucket)`: Placeholder for S3 upload.

#### [NEW] [__init__.py](file:///e:/TempFolder/Desktop_21_07_2025/Python/InstBot/insta-bot/automation/downloader/__init__.py)
- Regular init file.

## Verification Plan

### Automated Tests
- Create a script `test_downloader.py` and run it with sample URLs.
- Verify files are saved correctly in a `downloads` directory.
