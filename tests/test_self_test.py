import unittest

from validator.self_test import run_media_decoder_self_test


class PackagedScorerSelfTestTests(unittest.TestCase):
    def test_real_bounded_image_and_video_decoders(self):
        result = run_media_decoder_self_test()

        self.assertEqual(result["image"], "64x64 png/phash")
        self.assertEqual(result["video"], "64x64 mp4/4 frames")
