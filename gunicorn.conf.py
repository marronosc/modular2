import os

bind = "0.0.0.0:" + os.environ.get("PORT", "8080")
workers = 2
threads = 2
timeout = 120