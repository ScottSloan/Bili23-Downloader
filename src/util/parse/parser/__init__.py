class FavoriteParser:
    def __init__(self):
        self.success_callback = None

    def parse_favorite_list(self):
        if self.success_callback:
            self.success_callback([], {})

    def parse_subscription_list(self):
        if self.success_callback:
            self.success_callback([], {})

    def parse_follow_list(self, pn, type, follow_status):
        if self.success_callback:
            self.success_callback([], {})
