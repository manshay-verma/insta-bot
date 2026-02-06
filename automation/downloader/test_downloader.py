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
        mock_response.headers = {'Content-Type': 'image/jpeg', 'Content-Length': '4'}
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
        mock_response.headers = {'Content-Type': 'video/mp4', 'Content-Length': '10'}
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
        mock_response.headers = {'Content-Type': 'image/jpeg', 'Content-Length': '4'}
        mock_response.iter_content.return_value = [b'data']

        urls = ["https://example.com/1.jpg", "https://example.com/2.mp4"]
        filenames = ["1.jpg", "2.mp4"]
        results = self.downloader.bulk_download(urls, filenames)

        self.assertEqual(len(results), 2)
        for path in results:
            self.assertIsNotNone(path)
            self.assertTrue(os.path.exists(path))

    @patch('requests.get')
    def test_download_carousel(self, mock_get):
        # Mock responses for multiple items
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mock side effect for headers to handle different extensions in carousel
        def get_headers(url, *args, **kwargs):
            m = MagicMock()
            m.status_code = 200
            if 'item1' in url:
                m.headers = {'Content-Type': 'image/jpeg', 'Content-Length': '4'}
            else:
                m.headers = {'Content-Type': 'video/mp4', 'Content-Length': '10'}
            m.iter_content.return_value = [b'data']
            return m

        mock_get.side_effect = get_headers

        urls = ["https://example.com/item1.jpg", "https://example.com/item2.mp4"]
        base_filename = "carousel_post"
        results = self.downloader.download_carousel(urls, base_filename)

        self.assertEqual(len(results), 2)
        # Check that files were named correctly and order preserved
        self.assertEqual(os.path.basename(results[0]), "carousel_post_1.jpg")
        self.assertEqual(os.path.basename(results[1]), "carousel_post_2.mp4")
        for path in results:
            self.assertIsNotNone(path)
            self.assertTrue(os.path.exists(path))

    @patch('requests.get')
    def test_download_reel(self, mock_get):
        mock_response = MagicMock()
        mock_get.return_value = mock_response
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'reel_data']

        url = "https://example.com/reel.mp4"
        filename = "reel_test.mp4"
        filepath = self.downloader.download_reel(url, filename)

        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        self.assertEqual(os.path.basename(filepath), filename)

    @patch('requests.get')
    def test_download_story(self, mock_get):
        mock_response = MagicMock()
        mock_get.return_value = mock_response
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'story_data']

        url = "https://example.com/story.jpg"
        filename = "story_test.jpg"
        filepath = self.downloader.download_story(url, filename)

        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
        self.assertEqual(os.path.basename(filepath), filename)

    @patch('requests.get')
    def test_resume_download(self, mock_get):
        filename = "resume_test.mp4"
        filepath = os.path.join(self.download_dir, filename)
        
        # Create a partial file (5 bytes)
        with open(filepath, 'wb') as f:
            f.write(b'part1')
        
        # Mock initial response for headers
        mock_response_init = MagicMock()
        mock_response_init.status_code = 200
        mock_response_init.headers = {'Content-Type': 'video/mp4', 'Content-Length': '10'}
        
        # Mock resume response
        mock_response_resume = MagicMock()
        mock_response_resume.status_code = 206
        mock_response_resume.iter_content.return_value = [b'part2']
        
        # mock_get sequence: 1. initial check, 2. resume request
        mock_get.side_effect = [mock_response_init, mock_response_resume]
        
        url = "https://example.com/video.mp4"
        final_path = self.downloader.download_video(url, filename)
        
        self.assertEqual(final_path, filepath)
        with open(final_path, 'rb') as f:
            content = f.read()
        self.assertEqual(content, b'part1part2')
        
        # Verify Range header was sent in the second call
        self.assertEqual(mock_get.call_count, 2)
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs['headers']['Range'], 'bytes=5-')

    @patch('requests.get')
    def test_skip_already_downloaded(self, mock_get):
        filename = "already_done.jpg"
        filepath = os.path.join(self.download_dir, filename)
        
        # Create a complete file (4 bytes)
        with open(filepath, 'wb') as f:
            f.write(b'data')
            
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/jpeg', 'Content-Length': '4'}
        mock_get.return_value = mock_response
        
        url = "https://example.com/image.jpg"
        final_path = self.downloader.download_image(url, filename)
        
        self.assertEqual(final_path, filepath)
        # Should only have one call (the initial header check)
        self.assertEqual(mock_get.call_count, 1)
        # iter_content should NOT have been called
        mock_response.iter_content.assert_not_called()

    @patch('requests.get')
    def test_download_progress(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/jpeg', 'Content-Length': '10'}
        # Simulate download in 2 chunks of 5 bytes each
        mock_response.iter_content.return_value = [b'chunk', b'data!']
        mock_get.return_value = mock_response

        progress_calls = []
        def progress_cb(filename, current, total):
            progress_calls.append((filename, current, total))

        url = "https://example.com/test.jpg"
        filename = "progress_test.jpg"
        self.downloader.download_image(url, filename, progress_callback=progress_cb)

        # Check call count: 2 chunks = 2 calls
        self.assertEqual(len(progress_calls), 2)
        # First call: 5 bytes
        self.assertEqual(progress_calls[0], (filename, 5, 10))
        # Second call: 10 bytes
        self.assertEqual(progress_calls[1], (filename, 10, 10))

    @patch('requests.get')
    def test_organize_by_type(self, mock_get):
        """Test that files are organized by media type when organize_by_type is enabled."""
        downloader = MediaDownloader(download_dir=self.download_dir, organize_by_type=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/jpeg', 'Content-Length': '4'}
        mock_response.iter_content.return_value = [b'data']
        mock_get.return_value = mock_response

        url = "https://example.com/test.jpg"
        filename = "type_test.jpg"
        filepath = downloader.download_image(url, filename)

        self.assertIsNotNone(filepath)
        # Check that file is in the 'images' subdirectory
        expected_path = os.path.join(self.download_dir, "images", filename)
        self.assertEqual(filepath, expected_path)
        self.assertTrue(os.path.exists(filepath))

    @patch('requests.get')
    def test_organize_by_user(self, mock_get):
        """Test that files are organized by username when organize_by_user is enabled."""
        downloader = MediaDownloader(download_dir=self.download_dir, organize_by_user=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'video/mp4', 'Content-Length': '10'}
        mock_response.iter_content.return_value = [b'video_data']
        mock_get.return_value = mock_response

        url = "https://example.com/test.mp4"
        filename = "user_test.mp4"
        filepath = downloader.download_video(url, filename, username="testuser")

        self.assertIsNotNone(filepath)
        # Check that file is in the 'testuser' subdirectory
        expected_path = os.path.join(self.download_dir, "testuser", filename)
        self.assertEqual(filepath, expected_path)
        self.assertTrue(os.path.exists(filepath))

    @patch('requests.get')
    def test_organize_combined(self, mock_get):
        """Test that files are organized by username AND type when both are enabled."""
        downloader = MediaDownloader(download_dir=self.download_dir, organize_by_type=True, organize_by_user=True)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'video/mp4', 'Content-Length': '10'}
        mock_response.iter_content.return_value = [b'reel_data']
        mock_get.return_value = mock_response

        url = "https://example.com/reel.mp4"
        filename = "combined_test.mp4"
        filepath = downloader.download_reel(url, filename, username="instauser")

        self.assertIsNotNone(filepath)
        # Check that file is in the 'instauser/reels' subdirectory
        expected_path = os.path.join(self.download_dir, "instauser", "reels", filename)
        self.assertEqual(filepath, expected_path)
        self.assertTrue(os.path.exists(filepath))
if __name__ == '__main__':
    unittest.main()
