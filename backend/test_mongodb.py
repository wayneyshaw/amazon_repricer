from pymongo import Connection
import os
from urlparse import urlparse

MONGO_URL = os.environ.get('MONGOHQ_URL')
connection = Connection(MONGO_URL)
db = connection[urlparse(MONGO_URL).path[1:]]

print db.profiles.find_one()

