# encoding: utf-8

import requests

from django.config import settings
from django.core.management.base import BaseCommand, CommandError
from mlarchive.archive.utils import get_membership_3

import logging
logger = logging.getLogger(__name__)


def confirm_settings(names):
    for name in names:
        if not hasattr(settings, name):
            raise CommandError(f'{name} missing from settings')
        if not getattr(settings, name):
            raise CommandError(f'setting {name} empty')


class Command(BaseCommand):
    help = "Get private list membership from mailman 3 API."

    def add_arguments(self, parser):
        parser.add_argument('-q', '--quiet', action='store_true', dest='quiet', default=False,
            help="Don't print lists as they are processed")

    def handle(self, *args, **options):
        confirm_settings([
            'MAILMAN_API_USER',
            'MAILMAN_API_PASSWORD',
            'MAILMAN_API_ORIGIN',
            'MAILMAN_API_LISTS',
            'MAILMAN_API_MEMBER'])
        try:
            get_membership_3(quiet=options['quiet'])
        except requests.RequestException as e:
            logger.error(f'command get_membership failed: {e}')
            raise CommandError(f'Command failed. {e}')
