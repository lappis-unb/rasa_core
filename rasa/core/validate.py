import logging
import argparse
import asyncio
from rasa import utils
from typing import Text, List, BinaryIO, Any
from rasa.core.domain import Domain
from rasa_nlu.training_data.loading import load_data
from rasa.core.training.dsl import StoryFileReader
from rasa.core.training.dsl import UserUttered
from rasa.core.training.dsl import ActionExecuted

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()

parser.add_argument(
    '--domain', '-d',
    type=str, default='domain.yml',
    help='Path for the domain file'
)

parser.add_argument(
    '--stories', '-s',
    type=str, default='data/stories.md',
    help='Path for the stories file or directory'
)

parser.add_argument(
    '--intents', '-i',
    type=str, default='data/intents.md',
    help='Path for the intents file or directory'
)

parser.add_argument(
    '--warnings', '-w',
    action='store_true',
    default=False,
    help='Run script with warings'
)

parser.add_argument(
    '--skip-intents-validation', action='store_true', default=False,
    help='Skips validations to intents'
)

parser.add_argument(
    '--skip-utters-validation', action='store_true', default=False,
    help='Skips validations to utters'
)


class Validate:

    def __init__(self,
                 domain: Text,
                 intents: Text,
                 stories: Text,
                 warning: BinaryIO = True):
        self.domain = Domain.load(domain)
        self.intents = load_data(intents)
        self.warings = warning
        self.valid_intents = []
        self.valid_utters = []

        loop = asyncio.new_event_loop()
        self.stories = loop.run_until_complete(
            StoryFileReader.read_from_file(stories, self.domain))
        loop.close()

    def _search(self,
                vector: List[Any],
                searched_value: Any):
        vector.append(searched_value)
        count = 0
        while(searched_value != vector[count]):
            count += 1
        if(count == len(vector) - 1):
            return False
        else:
            return True

    def verify_intents(self):
        domain_intents = []
        files_intents = []

        for intent in self.domain.intent_properties:
            domain_intents.append(intent)

        for intent in self.intents._lazy_intent_examples:
            files_intents.append(intent.data['intent'])

        for intent in domain_intents:
            found = self._search(files_intents, intent)
            if not found:
                logger.error("The intent {} is in the domain file but "
                             "was not found in the intent files"
                             .format(intent))
            else:
                self.valid_intents.append(intent)

        for intent in files_intents:
            found = self._search(domain_intents, intent)
            if not found:
                logger.error("The intent {} is in the intents files but "
                             "was not found in the domain"
                             .format(intent))

    def verify_intents_in_stories(self):
        if self.valid_intents == []:
            self.verify_intents()

        stories_intents = []

        for story in self.stories:
            for event in story.events:
                if type(event) == UserUttered:
                    intent = event.intent["name"]
                    stories_intents.append(intent)
                    found = self._search(self.valid_intents, intent)

                    if not found:
                        logger.error("The intent {} is used in the "
                                     "stories files but it's not a "
                                     "valid intent".format(intent))

        if self.warings:
            for intent in self.valid_intents:
                found = self._search(stories_intents, intent)
                if not found:
                    logger.warning("The intent {} is not being used in any "
                                   "story".format(intent))

    def verify_utters(self):
        utter_actions = self.domain.action_names
        utter_templates = []

        for utter in self.domain.templates:
            utter_templates.append(utter)

        for utter in utter_templates:
            found = self._search(utter_actions, utter)
            if not found:
                logger.error("The utter {} is not listed in actions"
                             .format(utter))
            else:
                self.valid_utters.append(utter)

        for utter in utter_actions:
            if utter.split('_')[0] == 'utter':
                found = self._search(utter_templates, utter)
                if not found:
                    logger.error("There is no template for utter {}"
                                 .format(utter))

    def verify_utters_in_stories(self):
        if self.valid_utters == []:
            self.verify_utters()

        stories_utters = []

        for story in self.stories:
            for event in story.events:
                if type(event) == ActionExecuted:
                    utter = event.action_name
                    stories_utters.append(utter)
                    found = self._search(self.valid_utters, utter)

                    if not found:
                        logger.error("The utter {} is used in the "
                                     "stories files but it's not a "
                                     "valid utter".format(utter))

        if self.warings:
            for utter in self.valid_utters:
                found = self._search(stories_utters, utter)
                if not found:
                    logger.warning("The utter {} is not being used in any "
                                   "story".format(utter))

    def verify_all(self):
        logger.info("Verifying intents")
        self.verify_intents_in_stories()

        logger.info("Verifying utters")
        self.verify_utters_in_stories()


if __name__ == '__main__':
    domain = parser.parse_args().domain
    stories = parser.parse_args().stories
    intents = parser.parse_args().intents
    warning = parser.parse_args().warnings
    skip_intents_validation = parser.parse_args().skip_intents_validation
    skip_utters_validation = parser.parse_args().skip_utters_validation

    utils.configure_colored_logging(loglevel='DEBUG')

    validate = Validate(domain, intents, stories, warning)

    if not skip_utters_validation:
        logger.info("Verifying utters")
        validate.verify_utters_in_stories()

    if not skip_intents_validation:
        logger.info("Verifying intents")
        validate.verify_intents_in_stories()
