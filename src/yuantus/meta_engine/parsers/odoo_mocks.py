"""
Mocks for legacy Odoo models to support IR Rule adapter testing.
"""


class LegacyEnv:
    def __init__(self, user_id=None, context=None):
        self.user = MagicUser(user_id)
        self.context = context or {}


class MagicUser:
    def __init__(self, uid):
        self.id = uid
        self.company_id = 1
