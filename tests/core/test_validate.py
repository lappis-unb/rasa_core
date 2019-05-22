import pytest
import asyncio
from rasa.core.validate import Validate
from tests.core.conftest import DEFAULT_DOMAIN_PATH, DEFAULT_STORIES_FILE, DEFAULT_NLU_DATA
from rasa.core.domain import Domain
from rasa_nlu.training_data import load_data, TrainingData
from rasa.core.training.dsl import StoryFileReader

@pytest.fixture
def validate():
    domain = Domain.load(DEFAULT_DOMAIN_PATH)
    stories = asyncio.run(
        StoryFileReader.read_from_folder(DEFAULT_STORIES_FILE, domain)
    )
    intents = load_data(DEFAULT_NLU_DATA)

    return Validate(domain=domain, intents=intents, stories=stories)


def test_validate_creation(validate):
    assert isinstance(validate.domain, Domain)
    assert isinstance(validate.intents, TrainingData)
    assert isinstance(validate.stories, list)


def test_search(validate):
    vec = ['a', 'b', 'c', 'd', 'e']
    assert validate._search(vector=vec, searched_value='c')


def test_verify_intents(validate):
    valid_intents = ['greet', 'goodbye']
    validate.verify_intents()
    assert validate.valid_intents == valid_intents


def test_verify_utters(validate):
    valid_utterances = ['utter_greet', 'utter_goodbye', 'utter_default']
    validate.verify_utterances()
    assert validate.valid_utterances == valid_utterances
