import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from automation.downloader.media_downloader import MediaDownloader

class TestMediaDownloader(unittest.TestCase):

    def setUp(self):
        self.download_dir = "test_downloads"
        self.downloader = MediaDownloader(download_dir=self.download_dir)

    def tearDown(self):
        # Cleanup test downloads directory
        if os.path.exists(self.download_dir):
            import shutil
            shutil.rmtree(self.download_dir)

    @patch('requests.get')
    def test_download_image_success(self, mock_get):
        # Mocking the requests response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'data']
        mock_get.return_value = mock_response

        url = "https://example.com/test.jpg"
        filename = "test.jpg"
        filepath = self.downloader.download_image(url, filename)

        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        self.assertEqual(os.path.basename(filepath), filename)

    @patch('requests.get')
    def test_download_video_success(self, mock_get):
        mock_response = MagicMock()
        mock_get.return_value = mock_response
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'video_data']

        url = "https://example.com/test.mp4"
        filename = "test.mp4"
        filepath = self.downloader.download_video(url, filename)

        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        self.assertEqual(os.path.basename(filepath), filename)

    @patch('requests.get')
    def test_bulk_download(self, mock_get):
        mock_response = MagicMock()
        mock_get.return_value = mock_response
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'data']

        urls = ["https://example.com/1.jpg", "https://example.com/2.mp4"]
        filenames = ["1.jpg", "2.mp4"]
        results = self.downloader.bulk_download(urls, filenames)

        self.assertEqual(len(results), 2)
        for path in results:
            self.assertIsNotNone(path)
            self.assertTrue(os.path.exists(path))

if __name__ == '__main__':
    unittest.main()
