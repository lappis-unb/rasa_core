import logging
import argparse
from rasa_core import utils
from typing import Text, List, BinaryIO, Any
from rasa_core.domain import Domain
from rasa_nlu.training_data.loading import load_data
from rasa_core.training.dsl import StoryFileReader
from rasa_core.training.dsl import UserUttered
from rasa_core.training.dsl import ActionExecuted

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

class Validator:

    def __init__(self,
                 domain: Text,
                 intents: Text,
                 stories: Text,
                 warning: BinaryIO = True):
        self.domain = Domain.load(domain)
        self.intents = load_data(intents)
        self.stories = StoryFileReader.read_from_file(stories, self.domain)
        self.warings = warning
        self.valid_intents = []
        self.valid_utters = []
        ## Need to add the verifications for space between utters and stories
        ## format in the reader classes (Domain, StoryFileReader)

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

        ## Add domain intents in a list
        for intent in self.domain.intent_properties:
            domain_intents.append(intent)

        ## Add intents from the intents files to another list
        for intent in self.intents._lazy_intent_examples:
            files_intents.append(intent.data['intent'])

        ## Checks if the intents in the domain are the same as
        ## the ones in the files
        for intent in domain_intents:
            found = self._search(files_intents, intent)
            if not found:
                logger.error("The intent {} is in the domain file but "
                             "was not found in the intent files"
                             .format(intent))
            else:
                self.valid_intents.append(intent)

        ## Checks if the intents in the files are the same as
        ## the ones in the domain
        for intent in files_intents:
            found = self._search(domain_intents, intent)
            if not found:
                logger.error("The intent {} is in the intents files but "
                             "was not found in the domain"
                             .format(intent))

    def verify_intents_in_stories(self):
        ## Check if there is a list of valid intents
        if self.valid_intents == []:
            self.verify_intents()
        
        stories_intents = []

        ## Check if every intent in the storie files is a valid intent
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
            ## Check if the valid intents are being used in the stories
            for intent in self.valid_intents:
                found = self._search(stories_intents, intent)
                if not found:
                    logger.warning("The intent {} is not being used in any "
                                   "story".format(intent))

    def verify_utters(self):
        ## Make a list for utter actions and templates
        utter_actions = self.domain.action_names
        utter_templates = []

        for utter in self.domain.templates:
            utter_templates.append(utter)

        ## Check if every utter template has a action
        for utter in utter_templates:
            found = self._search(utter_actions, utter)
            if not found:
                logger.error("The utter {} is not listed in actions"
                              .format(utter))
            else:
                self.valid_utters.append(utter)

        ## Check if every utter action has a template
        for utter in utter_actions:
            if utter.split('_')[0] == 'utter':
                found = self._search(utter_templates, utter)
                if not found:
                    logger.error("There is no template for utter {}"
                                .format(utter))

    def verify_utters_in_stories(self):
        ## Check if there is a list of valid utters
        if self.valid_utters == []:
            self.verify_utters()
        
        stories_utters = []

        ## Check if every intent in the storie files is a valid intent
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
            ## Check if the valid utters are being used in the stories
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

    validator = Validator(domain, intents, stories, warning)

    if not skip_intents_validation:
        logger.info("Verifying intents")
        validator.verify_intents_in_stories()
    
    if not skip_utters_validation:
        logger.info("Verifying utters")
        validator.verify_utters_in_stories()
