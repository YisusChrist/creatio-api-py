import requests
import requests_cache


class SessionManager:
    def __init__(self, use_cache: bool = False, cache_expiration: int = 3600) -> None:
        self.session: requests.Session | requests_cache.CachedSession
        if use_cache:
            cached_backend = requests_cache.SQLiteCache(
                db_path="creatio_cache", use_cache_dir=True
            )
            self.session = requests_cache.CachedSession(
                backend=cached_backend, expire_after=cache_expiration
            )
        else:
            self.session = requests.Session()
