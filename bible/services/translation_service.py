# bible/services/translation_service.py

import logging

from .dbt.client import DBTClient

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Service to fetch translation data directly from the DBT API.
    """

    @classmethod
    def get_live_translations(cls, language_iso=None):
        """
        Fetches translations and filters out video content in-memory.

        Args:
            language_iso (str, optional): The language ISO code to filter by.
                Defaults to None.

        Returns:
            list: A list of translations with video content removed.
        """
        logger.info("Fetching live translations for language_iso: %s", language_iso)
        client = DBTClient()
        params = {'limit': 500}
        if language_iso:
            params['language_code'] = language_iso.upper()

        logger.debug("Requesting bibles with params: %s", params)

        try:
            response = client.get_bibles(**params)
            translations = response.get('data', [])
            logger.info("Received %d translations from DBT API.", len(translations))
            logger.debug("Raw translations from API: %s", translations)
        except Exception as e:
            logger.error(
                "DBT API Error fetching translations: %s", e, exc_info=True
            )
            return []

        return cls._process_translations(translations)

    @classmethod
    def _process_translations(cls, translations):
        """
        Removes video content and prepares fileset information.

        Args:
            translations (list): A list of translations to process.

        Returns:
            list: A list of processed translations with video content removed.
        """
        logger.info("Processing %d translations.", len(translations))
        processed = []
        for trans in translations:
            all_filesets = []
            for source, fileset_list in trans.get('filesets', {}).items():
                if source == 'dbp-vid':
                    continue

                non_video = [
                    fs
                    for fs in fileset_list
                    if 'video' not in fs.get('type', '')
                ]
                all_filesets.extend(non_video)

            if not all_filesets:
                logger.warning(
                    "No non-video filesets for translation %s. Skipping.",
                    trans.get('abbr'),
                )
                continue

            processed_filesets = []
            for fs in all_filesets:
                processed_filesets.append(
                    {
                        'id': fs.get('id'),
                        'type': fs.get('type'),
                        'size': fs.get('size'),
                    }
                )

            trans['filesets'] = processed_filesets
            processed.append(trans)

        logger.info(
            "Finished processing. Returning %d translations.", len(processed)
        )
        return processed
