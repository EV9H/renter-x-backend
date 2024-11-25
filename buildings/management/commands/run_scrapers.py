from django.core.management.base import BaseCommand
import asyncio
from buildings.sc.queue import ScraperQueue
import logging

class Command(BaseCommand):
    help = 'Run all configured scrapers'

    def handle(self, *args, **options):
        # Setup command-specific logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        self.stdout.write(self.style.SUCCESS('Starting scrapers...'))
        queue = ScraperQueue()
        
        try:
            asyncio.run(queue.process_queue())
            self.stdout.write(self.style.SUCCESS('Scraping completed successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Scraping failed: {str(e)}'))