import base64
import datetime
import json
import pytest
import os
from datetime import timezone 

from django.urls import reverse
from factories import EmailListFactory, MessageFactory
from mlarchive.archive.models import Subscriber, Message, EmailList


@pytest.mark.django_db(transaction=True)
def test_msg_counts_one_list(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=20130101'
    response = client.get(url)
    data = response.json()
    assert 'pubone' in data['msg_counts']
    assert data['msg_counts']['pubone'] == 5


@pytest.mark.django_db(transaction=True)
def test_msg_counts_two_lists(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone,pubtwo&start=20130101'
    response = client.get(url)
    data = response.json()
    assert 'pubone' in data['msg_counts']
    assert data['msg_counts']['pubone'] == 5
    assert 'pubtwo' in data['msg_counts']
    assert data['msg_counts']['pubtwo'] == 2


@pytest.mark.django_db(transaction=True)
def test_msg_counts_unknown_list(client, messages):
    url = reverse('api_msg_counts') + '?list=balloons&start=20130101'
    response = client.get(url)
    data = response.json()
    assert response.status_code == 404
    assert data == {'error': 'list not found'}


@pytest.mark.django_db(transaction=True)
def test_msg_counts_private_list(client, messages):
    url = reverse('api_msg_counts') + '?list=private&start=20130101'
    response = client.get(url)
    data = response.json()
    assert response.status_code == 404
    assert data == {'error': 'list not found'}


@pytest.mark.django_db(transaction=True)
def test_msg_counts_no_list(client, messages):
    '''Should return all public lists, no private'''
    url = reverse('api_msg_counts') + '?start=20130101'
    response = client.get(url)
    data = response.json()
    assert 'pubone' in data['msg_counts']
    assert data['msg_counts']['pubone'] == 5
    assert 'pubtwo' in data['msg_counts']
    assert data['msg_counts']['pubtwo'] == 2
    assert 'private' not in data['msg_counts']


@pytest.mark.django_db(transaction=True)
def test_msg_counts_no_date(client, messages):
    '''If no date provided return last month'''
    pubfour = EmailListFactory.create(name='pubfour')
    date = datetime.datetime.now(timezone.utc).replace(second=0, microsecond=0)
    MessageFactory.create(email_list=pubfour, date=date - datetime.timedelta(days=14))
    MessageFactory.create(email_list=pubfour, date=date - datetime.timedelta(days=35))
    url = reverse('api_msg_counts') + '?list=pubfour'
    response = client.get(url)
    data = response.json()
    assert 'pubfour' in data['msg_counts']
    assert data['msg_counts']['pubfour'] == 1


@pytest.mark.django_db(transaction=True)
def test_msg_counts_start(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=20130601'
    response = client.get(url)
    data = response.json()
    assert 'start' in data
    assert data['start'] == '20130601'
    assert 'pubone' in data['msg_counts']
    assert data['msg_counts']['pubone'] == 2


@pytest.mark.django_db(transaction=True)
def test_msg_counts_start_bad(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=142'
    response = client.get(url)
    data = response.json()
    assert response.status_code == 400
    assert data == {'error': 'invalid start date'}


@pytest.mark.django_db(transaction=True)
def test_msg_counts_end(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=20130101&end=20130601'
    response = client.get(url)
    data = response.json()
    assert 'end' in data
    assert data['end'] == '20130601'
    assert 'pubone' in data['msg_counts']
    assert data['msg_counts']['pubone'] == 3


@pytest.mark.django_db(transaction=True)
def test_msg_counts_end_bad(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=20200101&end=142'
    response = client.get(url)
    data = response.json()
    assert response.status_code == 400
    assert data == {'error': 'invalid end date'}


@pytest.mark.django_db(transaction=True)
def test_msg_counts_invalid_date(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&end=invalid'
    response = client.get(url)
    data = response.json()
    assert 'error' in data


@pytest.mark.django_db(transaction=True)
def test_msg_counts_duration_months(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=20130101&duration=1months'
    response = client.get(url)
    data = response.json()
    assert 'pubone' in data['msg_counts']
    assert data['msg_counts']['pubone'] == 1


@pytest.mark.django_db(transaction=True)
def test_msg_counts_duration_years(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=20130101&duration=1years'
    response = client.get(url)
    data = response.json()
    assert 'pubone' in data['msg_counts']
    assert data['msg_counts']['pubone'] == 3


@pytest.mark.django_db(transaction=True)
def test_msg_counts_duration_invalid(client, messages):
    url = reverse('api_msg_counts') + '?list=pubone&start=20130101&duration=1eon'
    response = client.get(url)
    data = response.json()
    assert response.status_code == 400
    assert data == {'error': 'invalid duration'}


@pytest.mark.django_db(transaction=True)
def test_subscriber_counts_one_list(client, subscribers):
    url = reverse('api_subscriber_counts') + '?list=pubone'
    response = client.get(url)
    data = response.json()
    print(data)
    print(vars(Subscriber.objects.first()))
    assert 'pubone' in data['subscriber_counts']
    assert data['subscriber_counts']['pubone'] == 5


@pytest.mark.django_db(transaction=True)
def test_subscriber_counts_no_lists(client, subscribers):
    url = reverse('api_subscriber_counts')
    response = client.get(url)
    data = response.json()
    print(data)
    print(vars(Subscriber.objects.first()))
    assert len(data['subscriber_counts']) == 2
    assert 'pubone' in data['subscriber_counts']
    assert data['subscriber_counts']['pubone'] == 5
    assert 'pubtwo' in data['subscriber_counts']
    assert data['subscriber_counts']['pubtwo'] == 3


@pytest.mark.django_db(transaction=True)
def test_subscriber_counts_date(client, subscribers):
    url = reverse('api_subscriber_counts') + '?list=pubtwo&date=2022-01-01'
    response = client.get(url)
    data = response.json()
    print(data)
    print(vars(Subscriber.objects.first()))
    assert 'pubtwo' in data['subscriber_counts']
    assert data['subscriber_counts']['pubtwo'] == 2


@pytest.mark.django_db(transaction=True)
def test_subscriber_counts_not_exist(client, subscribers):
    url = reverse('api_subscriber_counts') + '?list=pubtwo&date=2001-01-01'
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {}


def get_error_message(response):
    content = response.content.decode('utf-8')
    data_as_dict = json.loads(content)
    return data_as_dict['error']


@pytest.mark.django_db(transaction=True)
def test_import_message(client, settings):
    url = reverse('api_import_message')
    settings.API_KEYS = {url: 'valid_token'}
    path = os.path.join(settings.BASE_DIR, 'tests', 'data', 'mail.1')
    with open(path, 'rb') as f:
        message = f.read()
    message_b64 = base64.b64encode(message).decode()

    # test setup
    assert Message.objects.count() == 0
    assert EmailList.objects.filter(name='apple').exists() is False
    incoming_dir = settings.INCOMING_DIR
    assert os.path.isdir(incoming_dir)
    for file in os.listdir(incoming_dir):
        file_path = os.path.join(incoming_dir, file)
        os.remove(file_path)
    assert len(os.listdir(incoming_dir)) == 0

    # no api key
    response = client.post(
        url,
        {'list_name': 'apple', 'list_visibility': 'public', 'message': message_b64},
        headers={},
        content_type='application/json')
    assert response.status_code == 403

    # invalid api key
    response = client.post(
        url,
        {'list_name': 'apple', 'list_visibility': 'public', 'message': message_b64},
        headers={'X-API-Key': 'invalid_token'},
        content_type='application/json')
    assert response.status_code == 403

    # invalid visibility
    response = client.post(
        url,
        {'list_name': 'apple', 'list_visibility': 'opaque', 'message': message_b64},
        headers={'X-API-Key': 'valid_token'},
        content_type='application/json')
    assert response.status_code == 400

    # empty listname
    response = client.post(
        url,
        {'list_name': '', 'list_visibility': 'public', 'message': message_b64},
        headers={'X-API-Key': 'valid_token'},
        content_type='application/json')
    assert response.status_code == 400

    # valid request
    response = client.post(
        url,
        {'list_name': 'apple', 'list_visibility': 'public', 'message': message_b64},
        headers={'X-API-Key': 'valid_token'},
        content_type='application/json')
    assert response.status_code == 201

    # assert file exists in incoming
    assert len(os.listdir(incoming_dir)) == 1
    assert os.listdir(incoming_dir)[0].startswith('apple.public.')

    # assert list exists
    assert EmailList.objects.filter(name='apple', private=False).exists()

    # assert message exists, message-id
    msg = Message.objects.get(email_list__name='apple', msgid='0000000001@amsl.com')
    assert msg.subject == 'This is a test'

    # assert file exists in archive
    assert os.path.exists(msg.get_file_path())


@pytest.mark.django_db(transaction=True)
def test_import_message_private(client, settings):
    '''Ensure list_type variable is respected'''
    url = reverse('api_import_message')
    settings.API_KEYS = {url: 'valid_token'}
    path = os.path.join(settings.BASE_DIR, 'tests', 'data', 'mail.1')
    with open(path, 'rb') as f:
        message = f.read()
    message_b64 = base64.b64encode(message).decode()

    # test setup
    assert Message.objects.count() == 0
    assert EmailList.objects.filter(name='apple').exists() is False
    incoming_dir = settings.INCOMING_DIR
    assert os.path.isdir(incoming_dir)
    for file in os.listdir(incoming_dir):
        file_path = os.path.join(incoming_dir, file)
        os.remove(file_path)
    assert len(os.listdir(incoming_dir)) == 0

    # valid request
    response = client.post(
        url,
        {'list_name': 'apple', 'list_visibility': 'private', 'message': message_b64},
        headers={'X-API-Key': 'valid_token'},
        content_type='application/json')
    assert response.status_code == 201

    # assert file exists in incoming
    assert len(os.listdir(incoming_dir)) == 1
    assert os.listdir(incoming_dir)[0].startswith('apple.private.')

    # assert list exists
    assert EmailList.objects.filter(name='apple', private=True).exists()


@pytest.mark.django_db(transaction=True)
def test_import_message_failure(client, settings):
    '''Test various failure scenarios.'''
    url = reverse('api_import_message')
    settings.API_KEYS = {url: 'valid_token'}
    message = b'This is not an email'
    message_b64 = base64.b64encode(message).decode()

    # test setup
    assert Message.objects.count() == 0
    assert EmailList.objects.filter(name='apple').exists() is False
    incoming_dir = settings.INCOMING_DIR
    assert os.path.isdir(incoming_dir)
    for file in os.listdir(incoming_dir):
        file_path = os.path.join(incoming_dir, file)
        os.remove(file_path)
    assert len(os.listdir(incoming_dir)) == 0

    # valid request
    response = client.post(
        url,
        {'list_name': 'apple', 'list_visibility': 'public', 'message': message_b64},
        headers={'X-API-Key': 'valid_token'},
        content_type='application/json')
    assert response.status_code == 400

    # assert file exists in incoming
    assert len(os.listdir(incoming_dir)) == 1
    assert os.listdir(incoming_dir)[0].startswith('apple.public.')

    # assert list does not exist
    assert not EmailList.objects.filter(name='apple', private=False).exists()

    # assert message does not exist
    assert Message.objects.all().count() == 0
