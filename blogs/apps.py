from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class BlogsConfig(AppConfig):
    name = 'blogs'

    def ready(self):
        print("ʕ≧ᴥ≦ʔ Bear has been activated!")
        logger.error(f'ʕ≧ᴥ≦ʔ Bear has been activated!', exc_info=True)
        # logger.info("ʕ≧ᴥ≦ʔ Bear has been activated!")

