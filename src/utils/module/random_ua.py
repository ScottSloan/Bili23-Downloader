import random

class RandomUA:
    def get_platform():
        platform = [
            "Windows NT 10.0; Win64; x64",
            "Windows NT 10.0; ARM64; Win64",
            "X11; Linux x86_64",
            "X11; ARM64; Linux",
            "Macintosh; Intel Mac OS X 10_15_7",
            "Macintosh; ARM64 Mac OS X 11_2_3"
        ]

        return random.choice(platform)
    
    def get_version():
        return f"{random.randint(120, 136)}.0.0.0"

    @classmethod
    def get_browser(cls):
        browser = [
            "Chrome/{version} Safari/537.36 Edg/{version}",
            "Chrome/{version} Safari/537.36",
            "Version/13.1 Safari/537.36"
        ]

        return random.choice(browser).format(version = cls.get_version())

    @classmethod
    def get_random_ua(cls):
        return f"Mozilla/5.0 ({cls.get_platform()}) AppleWebKit/537.36 (KHTML, like Gecko) {cls.get_browser()}"