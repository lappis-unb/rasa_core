import logging
from typing import Text


logger = logging.getLogger(__name__)


class EventChannel(object):
    def publish(self, event: Text) -> None:
        """Publishes a json-formatted Rasa Core event into an event queue."""

        raise NotImplementedError("Event broker must implement the `publish` "
                                  "method")
