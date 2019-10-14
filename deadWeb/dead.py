"""Main application for dead-drop."""

from datetime import datetime
import hashlib
import json
from flask import Flask, render_template, send_from_directory, request, \
    Response, jsonify
from pymongo import MongoClient
from environs import Env
import uniqid


class DropHandler:
    """Handle drops, pickups and all the good stuff."""

    client = None
    client_hash = None
    salt = None

    def __init__(self, db):
        """Initialize class and setup connection to database."""
        env = Env()
        env.read_env()

        self.salt = env("SALT", "a6891cca-3ea1-4f56-b3a8-1d77095a088e")
        mongo_host = env("MONGO_HOST", "localhost")
        mongo_port = env("MONGO_PORT", "27017")
        mongo_timeout = env.int("MONGO_TIMEOUT", 5000)
        mongo_uri = "mongodb://{}:{}".format(mongo_host, mongo_port)

        # Accept db on init (for testing with mock)
        if not db:
            db = MongoClient(
                mongo_uri,
                connectTimeoutMS=mongo_timeout,
                serverSelectionTimeoutMS=mongo_timeout)
        self.client = db.dead

    def get_timed_key(self):
        """Return the timed_key."""
        drop_id = uniqid.uniqid()
        self.client.formKeys.insert_one({
            "key": drop_id,
            "created": datetime.now()})
        return drop_id

    def stats(self):
        """Return statistics."""
        pipeline = [
            {"$group": {
                "_id": {
                    "year": {"$year": "$createdDate"},
                    "month": {"$month": "$createdDate"},
                    "day": {"$dayOfMonth": "$createdDate"},
                    "userHash": "$userHash"},
                "count": {"$sum": 1}}},
            {"$group": {
                "_id": {
                    "year": "$_id.year",
                    "month": "$_id.month",
                    "day": "$_id.day"},
                "count": {"$sum": "$count"},
                "distinctCount": {"$sum": 1}}},
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
        ]

        cursor = self.client.track.aggregate(pipeline)
        return_data = []
        count_data = []
        unique_data = []

        for document in cursor:
            if document['_id'] == "1":
                continue
            datestamp = datetime(
                document['_id']['year'],
                document['_id']['month'],
                document['_id']['day'])
            count_data.append(
                [int(datestamp.strftime('%s')) * 1000, document['count'], ])
            unique_data.append(
                [int(datestamp.strftime('%s')) * 1000,
                 document['distinctCount']])

        def sort_by(a):
            return a[0]

        count_data = sorted(count_data, key=sort_by)
        unique_data = sorted(unique_data, key=sort_by)

        return_data.append({"label": "# of Drops", "data": count_data})
        return_data.append({"label": "Unique Users", "data": unique_data})

        return return_data

    def pickup(self, drop_id):
        """Handle a pickup."""
        document = self.client.drop.find_one_and_delete({"key": drop_id})

        if document == []:
            return []

        self.client.track.update(
            {"key": drop_id},
            {"$set": {"pickedUp": datetime.now()}, "$unset": {"key": ""}})

        # Handle old drops without createdDate
        if "createdDate" in document:
            # Do not return drops > 24 hours old
            time_delta = datetime.now() - document["createdDate"]

            if time_delta.days < 1:
                return document["data"]

        # no create date, no drop for you
        # too old, no drop for you
        return []

    def drop(self, data):
        """Create drop."""
        key = uniqid.uniqid()
        self.client.drop.insert_one({
            "key": key, "data": data, "createdDate": datetime.now()})
        self.client.track.insert_one({
            "key": key,
            "userHash": self.client_hash,
            "createdDate": datetime.now(),
            "pickedUp": None})
        return key

    def set_request_hash(self, ip_addr):
        """Set client_hash based on IP.

        We want to make sure people cant't use a rainbow table to look up IP's.
        """
        salted_ip = self.salt + ip_addr
        hasher = hashlib.sha256()
        hasher.update(salted_ip.encode('utf-8'))
        self.client_hash = hasher.hexdigest()[:32]


HANDLER = DropHandler(None)
APP = Flask(__name__)


@APP.route("/")
def index():
    """Return the index template."""
    return render_template('index.htm', timedKey=HANDLER.get_timed_key())


@APP.route("/stats")
def statsindex():
    """Return the stats."""
    return render_template('stats.htm')


@APP.route("/stats/json")
def statsjson():
    """Return the stats, in JSON."""
    key = HANDLER.stats()
    return Response(
        json.dumps(key, indent=4, sort_keys=True), mimetype='application/json')


@APP.route('/images/<path:path>')
def send_images(path):
    """Load images from drive path."""
    return send_from_directory('images', path)


@APP.route('/js/<path:path>')
def send_js(path):
    """Load js from drive path."""
    return send_from_directory('js', path)


@APP.route('/css/<path:path>')
def send_css(path):
    """Load css from drive path."""
    return send_from_directory('css', path)


@APP.route("/drop", methods=['POST'])
def drop():
    """Perform drop."""
    HANDLER.set_request_hash(request.remote_addr)
    key = HANDLER.drop(request.form["data"])
    return jsonify(id=key)


@APP.route("/pickup/<drop_id>")
def pickup_drop_index(drop_id):
    """Load the pickup HTML."""
    return render_template('index.htm', id=drop_id)


@APP.route("/getdrop.php?id=<drop_id>")
@APP.route("/drop/<drop_id>")
def pickup_drop_json(drop_id):
    """Actually get the drop from the DB."""
    return_data = HANDLER.pickup(drop_id)
    return Response(return_data, mimetype='application/json')


@APP.errorhandler(500)
def internal_server_error(e):
    """Handle server errors."""
    return render_template('error.htm'), 500
