import os
from urlparse import urlparse
from flask import Flask, request, Response
from functools import wraps
from pymongo import Connection
from werkzeug.security import check_password_hash,generate_password_hash
import json
import requests
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import time
from flask import jsonify
import boto

from datetime import timedelta
from flask import make_response, request, current_app
from functools import update_wrapper


def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers
            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            h['Access-Control-Allow-Credentials'] = 'true'
            h['Access-Control-Allow-Headers'] = \
                "Origin, X-Requested-With, Content-Type, Accept, Authorization"
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator

requests = requests.session()

FB_APP_SECRET = os.environ.get('FACEBOOK_SECRET')
FB_APP_ID = os.environ.get('FACEBOOK_APP_ID')

AWS_SECRET = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')

SELFIE_BUCKET = 'naderbuckets-selfie'
S3_BASE_URL = '.s3.amazonaws.com/'
SELFIE_SUFFIX = '_selfie.jpg'

print AWS_KEY
print AWS_SECRET

MONGO_URL = os.environ.get('MONGOHQ_URL')

if MONGO_URL:
  print 'FOUND_MONGO'
  # Get a connection
  connection = Connection(MONGO_URL)
  # Get the database
  db = connection[urlparse(MONGO_URL).path[1:]]
else:
  print 'NO_MONGO'
  # Not on an app with the MongoHQ add-on, do some localhost action
  connection = Connection('localhost', 27017)
  db = connection['MyDB']

app = Flask(__name__)
app.debug = True

artists = []

@app.route('/artists', methods=['POST', 'GET'])
@crossdomain(origin="*")
def create_artist():
    artist = request.form
    artists.append({'name': artist['name'], 'id':2, 'songs':[{'id':1, 'title':'byebyebye', 'rating':2}, {'id':1, 'title':'byebyebye', 'rating':2}]})

    print artist
    print artists
    if artist and artist != "":
        return json.dumps({'name': artist['name'], 'id':2, 'songs':[{'id':1, 'title':'byebyebye', 'rating':2}]})
    else:
        return json.dumps(artists)


@app.route('/songs', methods=['POST', 'GET'])
@crossdomain(origin="*")
def get_songs():
    return json.dumps([{'id':1, 'title':'byebyebye', 'rating':2}])



@app.route('/')
def main_server():
    print 'HELLO'
    return 'FUCK ME!'

def _fb_call(call, args=None):
    url = "https://graph.facebook.com/%s" % call
    r = requests.get(url, params=args)
    return json.loads(r.content)

def _is_valid_access_token(userid, access_token):
    r = requests.get('https://graph.facebook.com/%s?access_token=%s' % (userid, access_token))
    return r.status_code == 200

def _fetch_user_info(user_id, access_token):
    # We use the facebook graph API to get:
    #   basic_info: 'username', 'bio', 'first_name', 'last_name', 'verified',
    #               'name', 'locale', 'sports', 'quotes', 'link', 'email',
    #               'gender', 'timezone', 'updated_time', 'birthday', 'location',
    #               'hometown', 'employer', 'id'
    #   profile_pic
    #   friends: [(id, name), ...]
    #   photos: [{name, source, created_time, id}, ...]
    #
    #   Returned as a dictionary.
    print '1'
    print user_id
    print access_token
    basic_info = _fb_call(user_id,
                          args={'access_token':access_token})

    print '2'
    doc = basic_info
    doc['_id'] = basic_info.get('id')

    profile_pic = _fb_call('%s/picture' % user_id,
                          args={'access_token':access_token, 'width':'1000',
                                'height':'1000', 'redirect':'false'})
    profile_pic_source = profile_pic['data']['url']
    doc['profile_pic'] = profile_pic_source
    print '3'

    friends = _fb_call('%s/friends' % user_id,
                      args={'access_token': access_token})
    doc['friends'] = friends.get('data', {}) # XXX: Not 100% sure friends is a dictionary
    print '4'

    photos = _fb_call('%s/photos' % user_id,
                     args={'access_token': access_token, 'limit': 50})
    print '5'

    list_of_photos = []
    for photo in photos['data']:
        photo_map = dict((k, photo.get(k)) for k in ('name', 'source', 'created_time', 'id'))
        list_of_photos.append(photo_map)
    doc['photos'] = list_of_photos

    print '6'

    # XXX: Possibly use the access token to refresh the database.
    doc['access_token'] = access_token

    return doc

def _get_status_message(status_code, status_message):
    return json.dumps({'status_code':status_code,
                       'status_message':status_message})


@app.route('/create_user/', methods=['POST', 'GET'])
def create_user():
    # Check if a user is in the database. If he is, then do nothing.
    # If he isn't, fetch all his facebook info and add him to the db.

    # Extract the user id and access token.
    try:
        params = json.loads(request.data)
        access_token = params['access_token']
        user_id = params['user_id']
        user_name = params['user_name']
    except Exception as e:
        print 'Error parsing input params: %s' % e.__repr__()
        return (_get_status_message('create_user_error_1', 'PROBLEM: Error parsing input params %s' % e.__repr__()),
                400)

    # If we already have a database entry for this user, no need to fetch
    # anything.
    # XXX: Make it so this still fetches things in cases where the access ID
    #      is expired or something.
    u = db.profiles.find_one({'_id':user_id})
    if u and _is_valid_access_token(user_id, access_token):
        # XXX: Fetch data regardless of whether or not user
        #      already exists. Or check for staleness at least.
        print 'User %s already exists!' % (user_name)

        # Access token is valid so update the db with it.
        db.profiles.update(u, {'$set':{'access_token':access_token}})

        return json.dumps(u)

    try:
        print 'USER %s DID NOT EXIST.' % user_name
        #print 'OLD TOKEN: %s' % u.get('access_token')
        #print 'NEW TOKEN %s' % access_token
        doc = _fetch_user_info(user_id, access_token)
    except Exception as e:
        return (_get_status_message('create_user_error_2', 'PROBLEM: User did not exist before. '
                                            'Problem fetching basic facebook info: %s' % e.__repr__()),
                400)

    if u:
        # Possibly initalize values that aren't fetched.
        doc['balance']    = u.get('balance', 10)
        doc['my_bids']    = u.get('my_bids', {})
        doc['their_bids'] = u.get('their_bids', {})

        doc = dict(u.items() + doc.items())

    # Profile only gets created if user was authenticated by facebook.
    db.profiles.save(doc)

    return json.dumps(doc)

def _get_selfie_url(userid):
    return 'http://%s%s%s' % (SELFIE_BUCKET, S3_BASE_URL, userid + SELFIE_SUFFIX)

@app.route('/upload_selfie/<userid>', methods=['POST'])
def upload_selfie(userid):
    # XXX: Make it so that you need to pass in your access_token
    #      in order to post (to prevent people from posting on your behalf
    #      and causing mayhem).
    print 'PROCESSING SELFIE'
    u = db.profiles.find_one({'_id':userid})
    if not u:
        return (_get_status_message('upload_selfie_error_1', 'PROBLEM: user associated with '
                                            'id %s does not exist. Upload not allowed.' % userid),
                400)

    try:
        conn = S3Connection(AWS_KEY, AWS_SECRET)
        b = conn.get_bucket(SELFIE_BUCKET)
        k = Key(b)
        k.key = userid + SELFIE_SUFFIX
        k.set_contents_from_string(request.data) # f.read()

        selfie_url = _get_selfie_url(userid)
        db.profiles.update({'_id':userid}, {'$set' : {'selfie':selfie_url}})
    except Exception as e:
        return (_get_status_message('upload_selfie_error_2', 'PROBLEM: Could not add selfie to '
                                            'database. %s' % e.__repr__()),
                400)

    return (_get_status_message('', 'SUCCESS: Photo uploaded successfully.'),
            200)

@app.route('/potential_matches/<userid>', methods=['GET'])
def get_potential_matches(userid):
    print 'FINDING MATCHES'
    u = db.profiles.find_one({'_id':userid})
    if not u:
        return (_get_status_message('get_potential_matches_error_1', 'PROBLEM: user associated with '
                                            'id %s does not exist.' % userid),
                400)

    # XXX: return a json object with all the matches.
    potential_matches = list(db.profiles.find().limit(10))
    potential_matches = [x for x in potential_matches if x['gender'] != u['gender']]
    for x in potential_matches:
        x['access_token'] = None

    # Always return a dictionary no matter what.
    return json.dumps({'potential_matches':potential_matches})

@app.route('/potential_matches_by_location/<userid>/<lat>/<long>', methods=['GET'])
def get_potential_matches_by_location(userid, lat, long):
    print 'FINDING MATCHES BY LOCATION'

    u = db.profiles.find_one({'_id':userid})
    if not u:
        return (_get_status_message('get_potential_matches_by_location_error_1', 'PROBLEM: user associated with '
                                            'id %s does not exist.' % userid),
                400)

    try:
        lat = float(lat)
        long = float(long)

        # db.profiles.update({}, {$set:{'loc':[1.0,1.0]}}, {multi:1}}
        # x['results'][4]['obj']['name']

        potential_matches = list(db.profiles.find({"loc": {"$near": [long, lat]}, "gender" : {"$ne": u.get("gender", "female")}}).limit(10))
        for x in potential_matches:
            x['access_token'] = None
    except Exception as e:
        print 'Exception occurred in get_potential_matches_by_location: %s' % e.__repr__()
        return (_get_status_message('get_potential_matches_by_location_error_2', 'PROBLEM: lat/long not parseable -- %s' % e.__repr__()))

    # Always return a dictionary no matter what.
    return json.dumps({'potential_matches':potential_matches})

@app.route('/matches/<userid>', methods=['GET'])
def get_matches(userid):
    print 'FINDING MATCHES'
    u = db.profiles.find_one({'_id':userid})
    if not u:
        return (_get_status_message('get_potential_matches_error_1', 'PROBLEM: user associated with '
                                            'id %s does not exist.' % userid),
                400)

    if not u.get("matches"):
        return json.dumps({'matches':[]})
    else:
        # XXX: return a json object with all the matches.
        matches = [db.profiles.find_one({"_id":id}) for id in u.get("matches")]
        for x in matches:
            x['access_token'] = None
        # Always return a dictionary no matter what.
        return json.dumps({'matches':matches})

@app.route('/update_user_location/<userid>', methods=['POST'])
def update_user_location(userid):
    print 'UPDATING LOCATION'
    print request.data

    # Extract the user id and access token.
    try:
        params = json.loads(request.data)
        access_token = params['access_token']
        long = float(params['long'])
        lat = float(params['lat'])

        u = db.profiles.find_one({'_id' : userid})

    except Exception as e:
        print 'Error parsing input params: %s' % e.__repr__()
        return (_get_status_message('update_user_location_error_1', 'PROBLEM: Error parsing input params %s' % e.__repr__()),
                400)

    if u and _is_valid_access_token(userid, access_token):
        db.profiles.update({"_id":userid}, {"$set" : {"loc" : [long, lat]}})
        return (_get_status_message('', 'SUCCESS: User location updated properly.'),
                                    200)

    return (_get_status_message('update_user_location_error_2',
                                'PROBLEM: User %s not found OR access token is stale.' % userid))

def _delete_old_their_bids(my_doc, my_userid):
    old_my_bids = my_doc.get('my_bids', {})

    for their_userid, my_bid in old_my_bids.iteritems():
        # Get the other user and delete my_bid from their_bids.
        their_doc = db.profiles.find_one({'_id':their_userid})
        if not their_doc:
            print 'OTHER USER DOES NOT EXIST!'
        else:
            their_bids = their_doc.get('their_bids', {})
            their_bids.pop(my_userid, None)
            db.profiles.update({'_id':their_userid}, their_doc)
    # Now we remove all the bids from this
    my_doc['my_bids'] = {}
    db.profiles.update({'_id':my_userid}, my_doc)

def _update_their_bids(my_doc, my_userid, my_bids):
    for their_userid, my_bid in my_bids.iteritems():
        # Get the other user and add the my_bid to their_bids.
        their_doc = db.profiles.find_one({'_id':their_userid})
        if not their_doc:
            print 'OTHER USER DOES NOT EXIST!'
        else:
            their_bids = their_doc.get('their_bids', {})
            their_bids[my_userid] = int(my_bid)
            their_doc['their_bids'] = their_bids
            db.profiles.update({'_id':their_userid}, their_doc)

@app.route('/update_my_bids/<my_userid>', methods=['POST'])
def update_my_bids(my_userid):
    #print 'Data: %s' % request.data

    # Extract the user id and access token.
    try:
        params = json.loads(request.data)
        access_token = params['access_token']
        new_my_bids = params['my_bids']
    except Exception as e:
        print 'Error parsing input params: %s' % e.__repr__()
        return (_get_status_message('update_my_bids_error_1', 'PROBLEM: Error parsing input params %s' % e.__repr__()),
                400)

    #print my_userid
    u = db.profiles.find_one({'_id':my_userid})
    if not u:
        print 'User %s does NOT exist!' % (my_userid)
        return (_get_status_message('update_my_bids_error_2', 'PROBLEM: User does not exist. create_user first.'),
                400)

    if u.get('access_token') != access_token:
        return (_get_status_message('update_my_bids_error_3', 'PROBLEM: User access token is stale.'),
                400)

    balance  = u.get('balance', 10) # default to 10 if we don't find the balance...

    # CHANGE THIS CHECK IF YOU WANT A DIFFERENT BIDDING SCHEME.
    verified = all([balance >= int(bid) for other_user, bid in new_my_bids.iteritems()])
    new_my_bids.update((x, int(y)) for x, y in new_my_bids.items())

    if verified:
        # There are two things to consider. The person who is bidding (my) and the people
        # he is bidding on (they). We need to update both the database entry for my AND all
        # the database entries for they.
        _delete_old_their_bids(u, my_userid)
        db.profiles.update({'_id':my_userid}, {'$set' : {'my_bids':new_my_bids}})
        _update_their_bids(u, my_userid, new_my_bids)
        #print db.profiles.find({'_id':my_userid}, {'my_bids':1})

        #print my_userid
        #print db.profiles.find_one({'_id':my_userid})['my_bids']
    else:
        return (_get_status_message('update_my_bids_error_4', 'PROBLEM: User bid above balance on somebody somehow...'),
                400)

    return (_get_status_message('', 'SUCCESS: User my_bids properly processed.'),
            200)

@app.route('/get_their_bids/<userid>', methods=['GET'])
def get_their_bids(userid):
    # These are the bids made on userid by ANOTHER user.
    print 'GETTING BIDS'
    u = db.profiles.find_one({'_id':userid})
    if not u:
        return (_get_status_message('get_their_bids_error_1', 'PROBLEM: user associated with '
                                            'id %s does not exist.' % userid),
                400)

    # XXX: return a json object with all the bids.
    their_bids = u.get('their_bids')

    if their_bids is None:
        return (_get_status_message('get_their_bids_error_2', 'PROBLEM: Missing their_bids for user %s.' % userid),
                400)

    return json.dumps(their_bids)

@app.route('/get_my_bids/<userid>', methods=['GET'])
def get_my_bids(userid):
    # These are the bids made on userid by ANOTHER user.
    print 'GETTING BIDS'
    u = db.profiles.find_one({'_id':userid})
    if not u:
        return (_get_status_message('get_their_bids_error_1', 'PROBLEM: user associated with '
                                            'id %s does not exist.' % userid),
                400)

    # XXX: return a json object with all the bids.
    my_bids = u.get('my_bids')

    if my_bids is None:
        return (_get_status_message('get_their_bids_error_2', 'PROBLEM: Missing my_bids for user %s.' % userid),
                400)

    return json.dumps(my_bids)


if __name__ == '__main__':
  # Bind to PORT if defined, otherwise default to 5000.
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)
