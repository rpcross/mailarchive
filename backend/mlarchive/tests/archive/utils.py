import datetime
import mailbox
import pytest
import requests
from factories import EmailListFactory, UserFactory
from mock import patch
import os
import subprocess   # noqa
import xml.etree.ElementTree as ET

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from mlarchive.archive.utils import (get_noauth, get_lists, get_lists_for_user,
    lookup_user, process_members, get_membership, check_inactive, EmailList,
    create_mbox_file, _get_lists_as_xml, get_subscribers, Subscriber,
    get_known_mailman_lists, get_subscriber_count, get_subscribers_3,
    get_mailman_lists, get_membership_3)
from mlarchive.archive.models import User
from factories import EmailListFactory


@pytest.mark.django_db(transaction=True)
def test_get_noauth():
    user = UserFactory.create(username='noauth')
    EmailListFactory.create(name='public')
    private1 = EmailListFactory.create(name='private1', private=True)
    EmailListFactory.create(name='private2', private=True)
    private1.members.add(user)
    lists = get_noauth(user)
    assert len(lists) == 1
    assert lists == ['private2']


@pytest.mark.django_db(transaction=True)
def test_get_noauth_updates(settings):
    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    user = UserFactory.create(username='noauth')
    public = EmailListFactory.create(name='public')
    private = EmailListFactory.create(name='private', private=True)
    private.members.add(user)

    if user.is_anonymous:
        user_id = 0
    else:
        user_id = user.id

    key = '{:04d}-noauth'.format(user_id)
    print("key {}:{}".format(key, cache.get(key)))
    assert 'public' not in get_noauth(user)
    print("key {}:{}".format(key, cache.get(key)))
    # assert cache.get(key) == []
    public.private = True
    public.save()
    assert 'public' in get_noauth(user)
    print("key {}:{}".format(key, cache.get(key)))
    # assert False


@pytest.mark.django_db(transaction=True)
def test_get_lists():
    EmailListFactory.create(name='pubone')
    assert 'pubone' in get_lists()


@pytest.mark.django_db(transaction=True)
def test_get_lists_for_user(admin_user):
    EmailListFactory.create(name='public')
    private1 = EmailListFactory.create(name='private1', private=True)
    private2 = EmailListFactory.create(name='private2', private=True)
    user1 = UserFactory.create(username='user1')
    private1.members.add(user1)
    anonymous = AnonymousUser()
    print(anonymous.is_authenticated)
    print(EmailList.objects.filter(private=False).count())
    assert len(get_lists_for_user(admin_user)) == 3
    assert len(get_lists_for_user(anonymous)) == 1
    lists = get_lists_for_user(user1)
    assert private1.name in lists
    assert private2.name not in lists


@patch('requests.post')
def test_lookup_user(mock_post):
    response = requests.Response()
    # test error status
    response.status_code = 404
    mock_post.return_value = response
    user = lookup_user('joe@example.com')
    assert user is None
    # test no user object
    response.status_code = 200
    response._content = b'{"person.person": {"1": {"user": ""}}}'
    user = lookup_user('joe@example.com')
    assert user is None
    # test success
    response._content = b'{"person.person": {"1": {"user": {"username": "joe@example.com"}}}}'
    user = lookup_user('joe@example.com')
    assert user == 'joe@example.com'


@patch('requests.post')
@pytest.mark.django_db(transaction=True)
def test_process_members(mock_post):
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"person.person": {"1": {"user": {"username": "joe@example.com"}}}}'
    mock_post.return_value = response
    email_list = EmailListFactory.create(name='private', private=True)
    assert email_list.members.count() == 0
    process_members(email_list, ['joe@example.com'])
    assert email_list.members.count() == 1
    assert email_list.members.get(username='joe@example.com')


@patch('requests.post')
@pytest.mark.django_db(transaction=True)
def test_process_members_case_insensitive(mock_post):
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"person.person": {"1": {"user": {"username": "Joe@example.com"}}}}'
    mock_post.return_value = response
    email_list = EmailListFactory.create(name='private', private=True)
    user = User.objects.create(username='joe@example.com')
    email_list.members.add(user)
    assert email_list.members.count() == 1
    process_members(email_list, ['Joe@example.com'])
    assert email_list.members.count() == 1
    assert email_list.members.get(username='joe@example.com')


@patch('subprocess.check_output')
@patch('requests.post')
@pytest.mark.django_db(transaction=True)
def test_get_membership(mock_post, mock_output):
    # setup
    path = os.path.join(settings.EXPORT_DIR, 'email_lists.xml')
    if os.path.exists(path):
        os.remove(path)

    private = EmailListFactory.create(name='private', private=True)
    # handle multiple calls to check_output
    mock_output.side_effect = [b'private - Private Email List', b'joe@example.com']
    response = requests.Response()
    mock_post.return_value = response
    response.status_code = 200
    response._content = b'{"person.person": {"1": {"user": {"username": "joe@example.com"}}}}'
    assert private.members.count() == 0
    options = DummyOptions()
    options.quiet = True
    get_membership(options, None)
    assert private.members.count() == 1
    assert private.members.first().username == 'joe@example.com'
    assert os.path.exists(path)


@patch('requests.get')
@patch('requests.post')
@pytest.mark.django_db(transaction=True)
def test_get_membership_3(mock_post, mock_get):
    # setup
    path = os.path.join(settings.EXPORT_DIR, 'email_lists.xml')
    if os.path.exists(path):
        os.remove(path)

    private = EmailListFactory.create(name='bee', private=True)
    
    # prep mock
    response_lists = requests.Response()
    response_lists.status_code = 200
    response_lists._content = b'{"start": 0, "total_size": 1, "entries": [{"advertised": true, "display_name": "Bee", "fqdn_listname": "bee@lists.example.com", "list_id": "bee.lists.example.com", "list_name": "bee", "mail_host": "lists.example.com", "member_count": 1, "volume": 1, "description": "", "self_link": "http://172.19.199.3:8001/3.1/lists/bee.lists.example.com", "http_etag": "fb6d81b0f573936532b0b02d4d2116023a9e56a8"}], "http_etag": "ef59c8ea7baa670940fd87f99fce83ba5013381f"}'
    response_subscribers = requests.Response()
    response_subscribers.status_code = 200
    response_subscribers._content = b'{"start": 0, "total_size": 1, "entries": [{"email": "bperson@example.com", "http_etag": "\\"9baeb8580e60c8f5d3f0bab8d369ec8bff31a4b6\\""}], "http_etag": "\\"36668874b31dc412bf586dcdb7009f6524be1035\\""}'
    response_lookup = requests.Response()
    response_lookup.status_code = 200
    response_lookup._content = b'{"person.person": {"1": {"user": {"username": "bperson@example.com"}}}}'
    
    # handle multiple calls to mock_get
    mock_get.side_effect = [
        response_lists,
        response_subscribers]
    mock_post.return_value = response_lookup
    assert private.members.count() == 0
    options = DummyOptions()
    options.quiet = True
    get_membership_3(quiet=True)
    assert private.members.count() == 1
    assert private.members.first().username == 'bperson@example.com'
    assert os.path.exists(path)


class DummyOptions(object):
    pass


@patch('mlarchive.archive.utils.input')
@patch('subprocess.check_output')
@pytest.mark.django_db(transaction=True)
def test_check_inactive(mock_output, mock_input):
    mock_input.return_value = 'n'
    EmailListFactory.create(name='public')
    EmailListFactory.create(name='acme')
    support = EmailListFactory.create(name='support')

    # handle multiple calls to check_output
    mock_output.side_effect = [
        'public - Public Email List',
        'acme-arch:  "|/usr/home/call-archives.py acme"',
        'public - Public Email List',
        'acme-arch:  "|/usr/home/call-archives.py acme"',
    ]
    assert EmailList.objects.filter(active=True).count() == 3

    check_inactive(prompt=True)
    assert EmailList.objects.filter(active=True).count() == 3

    check_inactive(prompt=False)
    assert EmailList.objects.filter(active=True).count() == 2
    assert EmailList.objects.filter(active=False).first() == support


@pytest.mark.django_db(transaction=True)
def test_create_mbox_file(tmpdir, settings, latin1_messages):
    print('tmpdir: {}'.format(tmpdir))
    settings.ARCHIVE_MBOX_DIR = str(tmpdir)
    elist = EmailList.objects.get(name='acme')    
    first_message = elist.message_set.first()
    month = first_message.date.month
    year = first_message.date.year
    create_mbox_file(month=month, year=year, elist=elist)
    path = os.path.join(settings.ARCHIVE_MBOX_DIR, 'public', elist.name, '{}-{:02d}.mail'.format(year, month))
    assert os.path.exists(path)
    mbox = mailbox.mbox(path)
    assert len(mbox) == 1
    mbox.close()


@pytest.mark.django_db(transaction=True)
def test_get_lists_as_xml(client):
    private = EmailListFactory.create(name='private', private=True)
    EmailListFactory.create(name='public', private=False)
    user = UserFactory.create(username='test')
    private.members.add(user)
    xml = _get_lists_as_xml()
    root = ET.fromstring(xml)

    print(xml)

    public_anonymous = root.find("shared_root/[@name='public']").find("user/[@name='anonymous']")
    assert public_anonymous.attrib['access'] == 'read'

    private_anonymous = root.find("shared_root/[@name='private']").find("user/[@name='anonymous']")
    assert private_anonymous.attrib['access'] == 'none'

    private_test = root.find("shared_root/[@name='private']").find("user/[@name='test']")
    assert private_test.attrib['access'] == 'read,write'


@patch('subprocess.check_output')
@pytest.mark.django_db(transaction=True)
def test_get_subscribers(mock_output):
    public = EmailListFactory.create(name='public')
    # handle multiple calls to check_output
    mock_output.return_value = b'joe@example.com\nfred@example.com\n'
    subs = get_subscribers('public')
    assert subs == ['joe@example.com', 'fred@example.com']


@patch('subprocess.check_output')
@pytest.mark.django_db(transaction=True)
def test_get_subscriber_count(mock_output):
    public = EmailListFactory.create(name='public')

    # handle multiple calls to check_output
    mock_output.side_effect = [
        b'     public - Public List\n     private - Private List',
        b'joe@example.com\nfred@example.com\nmary@example.com\n',
    ]
    assert Subscriber.objects.count() == 0
    get_subscriber_count()
    subscriber = Subscriber.objects.first()
    assert subscriber.email_list == public
    assert subscriber.date == datetime.date.today()
    assert subscriber.count == 3


@patch('subprocess.check_output')
@pytest.mark.django_db(transaction=True)
def test_get_known_mailman_lists(mock_output):
    public = EmailListFactory.create(name='public')
    private = EmailListFactory.create(name='private', private=True)
    mock_output.return_value = b'    public - Public Email List\n   private - Private Email List'
    mlists = get_known_mailman_lists(private=True)
    assert len(mlists) == 1
    assert list(mlists) == [private]


@patch('requests.get')
@pytest.mark.django_db(transaction=True)
def test_get_mailman_lists(mock_get):
    ant = EmailListFactory.create(name='ant')
    bee = EmailListFactory.create(name='bee', private=True)
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"start": 0, "total_size": 2, "entries": [{"advertised": true, "display_name": "Ant", "fqdn_listname": "ant@lists.example.com", "list_id": "ant.lists.example.com", "list_name": "ant", "mail_host": "lists.example.com", "member_count": 0, "volume": 1, "description": "", "self_link": "http://172.19.199.3:8001/3.1/lists/ant.lists.example.com", "http_etag": "cb67744198a68efb427c24fab35d9fc593186d6c"}, {"advertised": true, "display_name": "Bee", "fqdn_listname": "bee@lists.example.com", "list_id": "bee.lists.example.com", "list_name": "bee", "mail_host": "lists.example.com", "member_count": 1, "volume": 1, "description": "", "self_link": "http://172.19.199.3:8001/3.1/lists/bee.lists.example.com", "http_etag": "fb6d81b0f573936532b0b02d4d2116023a9e56a8"}], "http_etag": "ef59c8ea7baa670940fd87f99fce83ba5013381f"}'
    mock_get.return_value = response
    mlists = get_mailman_lists(private=True)
    assert len(mlists) == 1
    assert list(mlists) == [bee]


@patch('requests.get')
@pytest.mark.django_db(transaction=True)
def test_get_subscribers_3(mock_get):
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"start": 0, "total_size": 1, "entries": [{"email": "bperson@example.com", "http_etag": "\\"9baeb8580e60c8f5d3f0bab8d369ec8bff31a4b6\\""}], "http_etag": "\\"36668874b31dc412bf586dcdb7009f6524be1035\\""}'
    mock_get.return_value = response
    public = EmailListFactory.create(name='public')
    subs = get_subscribers_3('public')
    assert subs == ['bperson@example.com']
