import os

HOUSES = ["Ravenclaw", "Hufflepuff", "Gryffindor", "Slytherin"]
SLACK_TOKEN = os.environ.get('SLACK_TOKEN') #'your_token_here'
# only prefects can add and remove multiple points
PREFECTS = os.environ.get('PREFECT_SLACK_IDS').split(',') #["your_slack_id_here", "someone_elses_here"]
# Announcers will be able to make the bot print the current standing
ANNOUNCERS = PREFECTS
CHANNEL = os.environ.get('CHANNEL_ID') # u'some_slack_channel_id'
IMAGE_PATH = "house_points.png"
POINTS_FILE = 'points.pkl' # todo: replace
