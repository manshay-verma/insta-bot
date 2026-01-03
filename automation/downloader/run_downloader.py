from media_downloader import *
downloader = MediaDownloader(download_dir="test_downloads")
video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
filename = "big_buck_bunny.mp4"
downloader.download_video(video_url, filename)