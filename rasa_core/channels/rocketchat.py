from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading
import queue

from flask import Blueprint, request, jsonify, make_response
from rocketchat_py_sdk import driver

from rasa_core.channels.channel import InputChannel, UserMessage, OutputChannel
from rasa_core.channels.rest import HttpInputComponent

logger = logging.getLogger(__name__)

class RocketChatInput(InputChannel):

    """RocketChat input channel implementation."""

    def __init__(self, user=None, password=None,
                 server_url='open.rocket.chat', ssl=True):

        self.user = user
        self.password = password
        self.server_url = server_url
        self.ssl = ssl

        self.rocketchat_bot = RocketChatBot(self.user, self.password,
                                            server=self.server_url,
                                            ssl=self.ssl)
        self.rocketchat_bot.start()
        self.rocketchat_bot.connector.add_prefix_handler('', self.register_message)

        self.message_queue = queue.Queue()

    def start_async_listening(self, message_queue):
        self._record_messages(message_queue.enqueue)

    def start_sync_listening(self, message_handler):
        self._record_messages(message_handler)

    def _record_messages(self, on_message):
        while self.rocketchat_bot.connector.connect:
            if not self.message_queue.empty():
                msg = self.message_queue.get()

                on_message(
                    UserMessage(msg['msg'], self.rocketchat_bot, msg['rid'])
                )

    def register_message(self, bot, message):
        self.message_queue.put(message)


class RocketChatBot(OutputChannel):
    def __init__(self, user, password, server, ssl):
        self.username = user
        self.password = password
        self.connector = driver.Driver(url=server , ssl=ssl)
        self.users = {}

    """
    Internal callback handlers
    """
    def method_callback(self, error, data):
        if error:
            logger.error('[-] callback error:')
            logger.error(error)
        else:
            logger.info("[+] callback success")
            logger.debug(data)

    """
    Public initializers
    """
    def start(self):
        self.connector.connect()
        self.connector.login(user=self.username, password=self.password,
                             callback=self.method_callback)
        self.connector.subscribe_to_messages()

    """
    Messages handlers
    """
    def send_text_message(self, recipient_id, message):
        if recipient_id not in self.users:
            self.users[recipient_id] = RocketchatHandleMessages(recipient_id, self)
        self.users[recipient_id].add_message(message)


class RocketchatHandleMessages:
    def __init__(self, rid, bot):
        self.rid = rid
        self.messages = []
        self.message_index = 0
        self.bot = bot

    def send_message(self):
        msg = self.messages[self.message_index]
        self.message_index += 1

        logger.info('[+] send message {}: {}'.format(self.rid, msg['message']))

        self.bot.connector.send_message(self.rid, msg['message'])

        if self.message_index == len(self.messages):
            logger.info('deactivate typing for {}'.format(self.rid))

            self.bot.connector.call(
                'stream-notify-room',
                [self.rid + '/typing', self.bot.username, False]
            )

            self.messages = []
            self.message_index = 0

    def add_message(self, message):
        logger.info('activate typing for {}'.format(self.rid))
        self.bot.connector.call(
            'stream-notify-room',
            [self.rid + '/typing', self.bot.username, True]
        )

        wait_time = 1

        if len(self.messages) != 0:
            last_msg = self.messages[-1]
            n_words = len(last_msg['message'].split(' '))

            words_per_sec = 5
            wait_time = max(1, n_words // words_per_sec) + last_msg['time']

        threading.Timer(wait_time, self.send_message).start()

        logger.info('[ ] schedule message {}: {}'.format(self.rid, message))
        self.messages.append({'message': message, 'time': wait_time})
