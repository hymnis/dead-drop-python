"""Tests for dead-drop."""

import pprint
import datetime
import hashlib
from unittest.mock import patch, ANY
from deadWeb.dead import  DropHandler
from freezegun import freeze_time


@patch('pymongo.MongoClient')
@freeze_time("2012-01-14")
def test_track_is_saved(mock_pymongo):
    """See if drop as tracked properly."""
    dead = DropHandler(mock_pymongo)
    dead.set_request_hash("127.0.0.1")
    data = {'test': "here"}
    dead.drop(data)
    mock_pymongo.dead.track.insert_one.assert_called_with({
        'key': ANY,
        'userHash': ANY,
        'createdDate': datetime.datetime(2012, 1, 14),
        'pickedUp': ANY})


@patch('pymongo.MongoClient')
@freeze_time("2012-01-14")
def test_user_hash_is_truncated(mock_pymongo):
    """See if client_hash is set properly."""
    dead = DropHandler(mock_pymongo)
    ip_addr = "127.0.0.1"
    dead.set_request_hash(ip_addr)
    data = {'test': "here"}
    dead.drop(data)

    salted_ip = DropHandler.salt + ip_addr
    hasher = hashlib.sha256()
    hasher.update(salted_ip.encode('utf-8'))
    client_hash = hasher.hexdigest()[:32]

    mock_pymongo.dead.track.insert_one.assert_called_with({
        'key': ANY,
        'userHash': client_hash,
        'createdDate': datetime.datetime(2012, 1, 14),
        'pickedUp': ANY})


@patch('pymongo.MongoClient')
@freeze_time("2012-01-14")
def test_drop_is_saved(mock_pymongo):
    """See if drop is saved properly."""
    dead = DropHandler(mock_pymongo)
    data = {"test": "here"}
    dead.drop(data)
    mock_pymongo.dead.drop.insert_one.assert_called_with({
        'key': ANY,
        'data': data,
        'createdDate': datetime.datetime(2012, 1, 14)})


@patch('pymongo.MongoClient')
@freeze_time("2012-01-14")
def test_drop_deleted_when_accessed(mock_pymongo):
    """See if drop is deleted properly when accessed."""
    sample_drop = get_sample_drop()
    mock_pymongo.dead.drop.find_one_and_delete.return_value = sample_drop
    dead = DropHandler(mock_pymongo)
    pprint.pprint("XXXXX")
    pprint.pprint(sample_drop)
    val = dead.pickup(sample_drop['key'])

    pprint.pprint(val)
    mock_pymongo.dead.drop.find_one_and_delete.assert_called_with({
        'key': sample_drop['key']})
    assert sample_drop['data'] == val


@patch('pymongo.MongoClient')
@freeze_time("2012-01-14")
def test_track_updated_when_accessed(mock_pymongo):
    """See if track is updated when accessed."""
    sample_drop = get_sample_drop()
    mock_pymongo.dead.drop.find_one_and_delete.return_value = sample_drop
    dead = DropHandler(mock_pymongo)
    val = dead.pickup(sample_drop['key'])
    mock_pymongo.dead.track.update.assert_called_with(
        {"key": sample_drop['key']},
        {
            "$set": {"pickedUp": datetime.datetime(2012, 1, 14)},
            "$unset": {"key": ""}})
    assert sample_drop["data"] == val


@patch('pymongo.MongoClient')
def test_stats_returned(mock_pymongo):
    """See if stats are returned properly."""
    mock_pymongo.dead.track.find.return_value = get_sample_stats()
    dead = DropHandler(mock_pymongo)
    stats = dead.stats()
    expected = [
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
    mock_pymongo.dead.track.aggregate.assert_called_with(expected)


@patch('pymongo.MongoClient')
@freeze_time("2012-01-14")
def test_drop_not_returned_when_no_create_date(mock_pymongo):
    """See if drop is returned when there's no create date."""
    # (to handle old drops)
    sample_drop = get_sample_drop()
    sample_drop.pop('createdDate')
    mock_pymongo.dead.drop.find_one_and_delete.return_value = sample_drop
    dead = DropHandler(mock_pymongo)
    val = dead.pickup(sample_drop['key'])
    pprint.pprint(sample_drop)
    pprint.pprint(val)

    mock_pymongo.dead.drop.find_one_and_delete.assert_called_with({
        'key': sample_drop['key']})
    assert val == []


@patch('pymongo.MongoClient')
@freeze_time("2012-01-14")
def test_drop_deleted_and_not_returned_when_24hours_old(mock_pymongo):
    """See if drop is returned when it's more than 24 h old."""
    key = "anything"
    sample_drop = get_sample_drop()
    sample_drop['createdDate'] = datetime.datetime(2012, 1, 12)
    mock_pymongo.dead.drop.find.return_value = [sample_drop]
    dead = DropHandler(mock_pymongo)
    val = dead.pickup(key)

    assert val == []
    mock_pymongo.dead.drop.find_one_and_delete.assert_called_with({'key': key})


@patch('pymongo.MongoClient')
def test_return_none_when_not_existing(mock_pymongo):
    """See if none is returned if drop doesn't exist."""
    sample_drop = get_sample_drop()
    mock_pymongo.dead.drop.find_one_and_delete.return_value = []
    dead = DropHandler(mock_pymongo)
    val = dead.pickup(sample_drop['key'])

    assert val == []
    mock_pymongo.dead.drop.find_one_and_delete.assert_called_with({
        'key': sample_drop['key']})


@patch('pymongo.MongoClient')
def test_timed_key_is_saved(mock_pymongo):
    """See if timed key is saved."""
    dead = DropHandler(mock_pymongo)
    timed_key = dead.get_timed_key()
    mock_pymongo.dead.formKeys.insert_one.assert_called_with({
        'key': timed_key, "created": ANY})


# Helper methods
def get_sample_stats():
    """Return sample stats for testing."""
    samplestats = [
        {"_id": {"year": 2018, "month": 3, "day": 2},
         "count": 67, "distinctCount": 49},
        {"_id": {"year": 2018, "month": 3, "day": 3},
         "count": 24, "distinctCount": 15}
    ]

    return samplestats


def get_sample_drop():
    """Return some sample drops."""
    return {
        'key': '12345',
        'data': "test data return",
        'createdDate': datetime.datetime.now()}
