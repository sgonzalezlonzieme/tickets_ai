from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from clients.rate_limit import RateLimiter, RateLimitStore, get_rate_limiter
from clients.rate_limit.config import RateLimitSettings


class Clock:
    def __init__(self):
        self.now=100.0
        self.waits=[]

    def time(self):
        return self.now

    def sleep(self,seconds):
        self.waits.append(seconds)
        self.now+=seconds


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.directory=TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path=Path(self.directory.name)/'requests.sqlite3'
        self.clock=Clock()

    def limiter(self,provider='openai',limit=2):
        return RateLimiter(provider,limit,RateLimitStore(self.path),self.clock.time,self.clock.sleep)

    def test_within_quota_does_not_wait(self):
        limiter=self.limiter()
        limiter.acquire()
        limiter.acquire()
        self.assertEqual(self.clock.waits,[])

    def test_exhaustion_waits_and_continues(self):
        limiter=self.limiter()
        for _ in range(3):
            limiter.acquire()
        self.assertEqual(self.clock.waits,[60.0])

    def test_waits_only_until_oldest_request_expires(self):
        limiter=self.limiter()
        limiter.acquire()
        self.clock.now+=20
        limiter.acquire()
        limiter.acquire()
        self.assertEqual(self.clock.waits,[40.0])

    def test_providers_have_independent_quotas(self):
        self.limiter('openai',1).acquire()
        self.limiter('gemini',1).acquire()
        self.assertEqual(self.clock.waits,[])

    def test_new_instances_share_saved_quota(self):
        self.limiter(limit=1).acquire()
        self.limiter(limit=1).acquire()
        self.assertEqual(self.clock.waits,[60.0])

    def test_exact_window_boundary_is_available(self):
        self.limiter(limit=1).acquire()
        self.clock.now+=60
        self.limiter(limit=1).acquire()
        self.assertEqual(self.clock.waits,[])

    def test_default_and_configured_quota(self):
        get_rate_limiter.cache_clear()
        self.addCleanup(get_rate_limiter.cache_clear)
        self.assertEqual(RateLimitSettings().requests_per_minute,10)
        with patch('clients.rate_limit.config.dotenv_values',return_value={'OPENAI_REQUESTS_PER_MINUTE':'4'}):
            self.assertEqual(get_rate_limiter('openai')._limit,4)
            self.assertEqual(get_rate_limiter('gemini')._limit,10)

    def test_invalid_limit_is_rejected(self):
        for value in [0,-1,'abc',1.5,None]:
            with self.subTest(value=value),self.assertRaises(ValidationError):
                RateLimitSettings(requests_per_minute=value)
