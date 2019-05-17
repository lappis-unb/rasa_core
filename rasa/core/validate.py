import logging
import argparse
import asyncio
from rasa import utils
from typing import Text, List, BinaryIO, Any
from rasa.core.domain import Domain
from rasa.nlu.training_data import load_data, TrainingData
from rasa.core.training.dsl import StoryFileReader, StoryStep
from rasa.core.training.dsl import UserUttered
from rasa.core.training.dsl import ActionExecuted
from rasa.core import cli

logger = logging.getLogger(__name__)


def create_argument_parser():
    """Parse all the command line arguments for the run script."""

    parser = argparse.ArgumentParser(description="Validates files")

    parser.add_argument(
        "--domain", "-d", type=str, required=True, help="Path for the domain file"
    )

    parser.add_argument(
        "--stories",
        "-s",
        type=str,
        required=True,
        help="Path for the stories file or directory",
    )

    parser.add_argument(
        "--intents",
        "-i",
        type=str,
        required=True,
        help="Path for the intents file or directory",
    )

    parser.add_argument(
        "--skip-intents-validation",
        action="store_true",
        default=False,
        help="Skips validations to intents",
    )

    parser.add_argument(
        "--skip-utters-validation",
        action="store_true",
        default=False,
        help="Skips validations to utters",
    )

    cli.arguments.add_logging_option_arguments(parser)
    cli.run.add_run_arguments(parser)
    return parser


class Validate:
    def __init__(self, domain: Domain, intents: TrainingData, stories: List[StoryStep]):
        self.domain = domain
        self.intents = intents
        self.valid_intents = []
        self.valid_utters = []
        self.stories = stories

    def _search(self, vector: List[Any], searched_value: Any):
        vector.append(searched_value)
        count = 0
        while searched_value != vector[count]:
            count += 1
        if count == len(vector) - 1:
            return False
        else:
            return True

    def verify_intents(self):
        domain_intents = []
        files_intents = []

        for intent in self.domain.intent_properties:
            domain_intents.append(intent)

        for intent in self.intents._lazy_intent_examples:
            files_intents.append(intent.data["intent"])

        for intent in domain_intents:
            found = self._search(files_intents, intent)
            if not found:
                logger.error(
                    "The intent {} is in the domain file but "
                    "was not found in the intent files".format(intent)
                )
            else:
                self.valid_intents.append(intent)

        for intent in files_intents:
            found = self._search(domain_intents, intent)
            if not found:
                logger.error(
                    "The intent {} is in the intents files but "
                    "was not found in the domain".format(intent)
                )

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
                        logger.error(
                            "The intent {} is used in the "
                            "stories files but it's not a "
                            "valid intent".format(intent)
                        )

        for intent in self.valid_intents:
            found = self._search(stories_intents, intent)
            if not found:
                logger.warning(
                    "The intent {} is not being used in any " "story".format(intent)
                )

    def verify_utters(self):
        utter_actions = self.domain.action_names
        utter_templates = []

        for utter in self.domain.templates:
            utter_templates.append(utter)

        for utter in utter_templates:
            found = self._search(utter_actions, utter)
            if not found:
                logger.error("The utter {} is not listed in actions".format(utter))
            else:
                self.valid_utters.append(utter)

        for utter in utter_actions:
            if utter.split("_")[0] == "utter":
                found = self._search(utter_templates, utter)
                if not found:
                    logger.error("There is no template for utter {}".format(utter))

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
                        logger.error(
                            "The utter {} is used in the "
                            "stories files but it's not a "
                            "valid utter".format(utter)
                        )

        for utter in self.valid_utters:
            found = self._search(stories_utters, utter)
            if not found:
                logger.warning(
                    "The utter {} is not being used in any " "story".format(utter)
                )

    def verify_all(self):
        logger.info("Verifying intents")
        self.verify_intents_in_stories()

        logger.info("Verifying utters")
        self.verify_utters_in_stories()


if __name__ == "__main__":
    parser = create_argument_parser()
    cmdline_args = parser.parse_args()

    domain = Domain.load(cmdline_args.domain)
    stories = asyncio.run(
        StoryFileReader.read_from_folder(cmdline_args.stories, domain)
    )
    intents = load_data(cmdline_args.intents)
    skip_intents_validation = cmdline_args.skip_intents_validation
    skip_utters_validation = cmdline_args.skip_utters_validation

    utils.configure_colored_logging(cmdline_args.loglevel)
    validate = Validate(domain, intents, stories)

    if not skip_utters_validation:
        logger.info("Verifying utters")
        validate.verify_utters_in_stories()
    if not skip_intents_validation:
        logger.info("Verifying intents")
        validate.verify_intents_in_stories()
