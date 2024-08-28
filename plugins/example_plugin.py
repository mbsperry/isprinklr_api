# Example of a notification plugin

from .context import scheduler
import requests
import logging

logger = logging.getLogger(__name__)

class ExamplePlugin(scheduler.BasePlugin):
    def __init__(self):
        self.notification_url = "https://httpbin.org/post"

    def send_notification(self, message):
        try:
            print(f"Sending notification: {message}")
            logger.debug(f"Sending notification: {message}")
            requests.post(self.notification_url, json={"message": message})
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def on_schedule_start(self):
        self.send_notification("Sprinkler schedule started")

    def on_schedule_end(self):
        self.send_notification("Sprinkler schedule completed")

    def on_error(self, error_message):
        self.send_notification(f"Error running schedule: {error_message}")