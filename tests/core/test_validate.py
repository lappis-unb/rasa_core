import asyncio
from rasa.core.validate import Validate

domain_file = 'data/test_validate/domain.yml'
intents_file = 'data/test_validate/intents.md'
stories_file = 'data/test_validate/stories.md'

validate_test = Validate(domain=domain_file,
                        intents=intents_file,
                        stories=stories_file)


def test_validate_creation():

    assert isinstance(validate_test.domain, Domain)
    assert isinstance(validate_test.intents, TrainingData)
    assert isinstance(validate_test.stories, list)


def test_search():
    vec = ['a', 'b', 'c', 'd', 'e']
    assert validate_test._search(vector=vec, searched_value='c')


def test_verify_intents():
    valid_intents = ['greet', 'goodbye', 'affirm', 'deny']

    validate_test.verify_intents()
    assert validate_test.valid_intents == valid_intents


def test_verify_utters():
    valid_utters = ['utter_greet', 'utter_goodbye', 'utter_question']

    validate_test.verify_utters()
    assert validate_test.valid_utters == valid_utters
