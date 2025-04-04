from django.core.management.base import ArgumentParser, BaseCommand
from django.db.models import Q

from streams.models import Stream
from streams.tasks._process import process_stream


class Command(BaseCommand):

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument('-r', '--run', action='store_true', default=False)
        parser.add_argument('stream_type', nargs='*')

    def handle(self, *args, **options):
        cond = Q()
        if options['stream_type']:
            cond |= Q(stream_type__in=options['stream_type'])
        grouped_streams = {}
        for stream in Stream.objects.filter(cond).order_by('id'):
            grouped_streams.setdefault(stream.stream_type, []).append(stream)


        for stream_type, streams in grouped_streams.items():
            print(stream_type, len(streams))
            for stream in streams:
                print(f'\t{stream.id}\t{stream}')
                if options['run']:
                    process_stream(stream.id, False)
