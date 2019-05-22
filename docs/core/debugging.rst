:desc: Read more how to learn from real user input and behaviour by debugging
       your contextual AI assistants and chatbots using open source libraries.

.. _debugging:

Debugging
=========

.. note::

   Wherever you are talking to the bot (command line, slack, facebook, etc), you can
   clear the tracker and start a new conversation by sending the message ``/restart``.


To debug your bot, run it on the command line with the ``--debug`` flag.

For example:

.. code-block:: bash

  python3 -m rasa.core.run -d models/dialogue -u models/nlu/current --debug


This will print lots of information to help you understand what's going on.
For example:

.. code-block:: bash
   :linenos:

    Bot loaded. Type a message and press enter:
    /greet
    rasa.core.tracker_store - Creating a new tracker for id 'default'.
    rasa.core.processor - Received user message '/greet' with intent '{'confidence': 1.0, 'name': 'greet'}' and entities '[]'
    rasa.core.processor - Logged UserUtterance - tracker now has 2 events
    rasa.core.processor - Current slot values:

    rasa.core.policies.memoization - Current tracker state [None, {}, {'prev_action_listen': 1.0, 'intent_greet': 1.0}]
    rasa.core.policies.memoization - There is a memorised next action '2'
    rasa.core.policies.ensemble - Predicted next action using policy_0_MemoizationPolicy
    rasa.core.policies.ensemble - Predicted next action 'utter_greet' with prob 1.00.
    Hey! How are you?


Line number ``4`` tells us the result of NLU parsing the message 'hello'.
If NLU makes a mistake, your Core model won't know how to behave. A common
source of errors is that your NLU model didn't accurately pick the intent,
or made a mistake when extracting entities. If this is the case, you probably
want to go and improve your NLU model.

If any slots are set, those will show up in line ``6``.
and in lines ``9-11`` we can see which policy was used to
predict the next action.
If this exact story was already in the training data and the
``MemoizationPolicy`` is part of the ensemble, this will be used to predict
the next action with probability 1.

If all the slot and NLU information is correct but the wrong action
is still predicted, you should check which policy was used to make
the prediction. If the prediction came from the ``MemoizationPolicy``,
then there is an error in your stories. If a probabilistic policy
like the ``KerasPolicy`` was used, then your model just made a
prediction that wasn't right. In that case it is a good idea to run
the bot with interactive learning switched on so you can
create the relevant stories to add to your training data.


.. _story-visualization:

Visualizing your Stories
------------------------

Sometimes it is helpful to get an overview of the conversational paths that
are described within a story file. To make debugging easier and to ease
discussions about bot flows, you can visualize the content of a story file.

You can visualize stories with this command:

..  code-block:: bash

   cd examples/concertbot/
   python3 -m rasa.core.visualize -d domain.yml -s data/stories.md -o graph.html -c config.yml

This will run through the stories of the ``concertbot`` example in
``data/stories.md`` and create a graph which can be shown in your browser by
opening ``graph.html`` with browser of your choice.

.. image:: _static/images/concert_stories.png

We can also run the visualisation directly from code. For this example, we can
create a ``visualize.py`` in ``examples/concertbot`` with the following code:

.. literalinclude:: ../../examples/concertbot/visualize.py

Which will create the same image as the previous command.
The graph we show here is still very simple, graphs can quickly get very complex.

You can make your graph a little easier to read by replacing the user messages
with real examples from your nlu data. To do this, use the ``nlu_data`` flag,
for example ``--nlu_data mydata.json``.

.. note::

   The story visualization needs to load your domain. If you have
   any custom actions written in python make sure they are part of the python
   path, and can be loaded by the visualization script using the module path
   given for the action in the domain (e.g. ``actions.ActionSearchVenues``).

Test files for possible mistakes
--------------------------------

To verify if there is any mistake in your domain, intents and stories files, run the validate script.
You can run it with the following command:

.. code-block:: bash

  $ python -m rasa.core.validate -s data/stories.md -d domain.yml -i data/nlu.md

The script above runs all the validations on your files. Here is the list of options to
the script:

.. program-output:: python -m rasa.core.validate --help 

You can also run the functions on your train.py or other scripts. Here is
a list of functions for the Validate class:

**verify_intents():** Checks if intents listed in domain file are the same of the ones in the intent files.

**verify_intents_in_stories():** Verification for intents in the stories, to check if they are valid.

**verify_utterances():** Checks if utterances listed in actions are the same of the ones in the templates.

**verify_utterances_in_stories():** Verification for utterances in stories, to check if they are valid.

**verify_all():** Runs all verifications above.

To use these functions it is necessary to create a Validate object and initialize the logger. See the following code:

.. code-block:: python

  import logging
  from rasa import utils
  from rasa.core.validate import Validate

  logger = logging.getLogger(__name__)

  utils.configure_colored_logging('DEBUG') 

  domain = Domain.load('domain.yml')
  intents = load_data('data/intents')
  stories = asyncio.run(
      StoryFileReader.read_from_folder('data/stories', domain)
  )

  validate = Validate(domain=domain,
                      intents=intents,
                      stories=stories)

  validate.verify_all()

.. include:: feedback.inc
