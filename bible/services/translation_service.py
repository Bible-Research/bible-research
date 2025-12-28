# bible/services/translation_service.py

from .dbt.client import DBTClient


class TranslationService:
    """
    Service to fetch translation data directly from the DBT API.
    """

    @classmethod
    def get_live_translations(cls, language_iso=None):
        """Fetches translations and filters out video content in-memory."""
        client = DBTClient()
        params = {'limit': 500}
        if language_iso:
            params['language_code'] = language_iso.upper()

        try:
            response = client.get_bibles(**params)
            translations = response.get('data', [])
        except Exception as e:
            # In case the API fails, return an empty list
            print(f"DBT API Error fetching translations: {e}")
            return []

        # Process translations to remove video and simplify format info
        return cls._process_translations(translations)

    @classmethod
    def _process_translations(cls, translations):
        """Removes video content and prepares fileset information."""
        processed = []
        for trans in translations:
            all_filesets = []
            for source, fileset_list in trans.get('filesets', {}).items():
                if source != 'dbp-vid':
                    # Filter out video filesets
                    non_video = [
                        fs for fs in fileset_list
                        if 'video' not in fs.get('type', '')
                    ]
                    all_filesets.extend(non_video)

            if not all_filesets:
                continue  # Skip translations with only video

            # Process filesets for frontend
            processed_filesets = []
            for fs in all_filesets:
                processed_filesets.append({
                    'id': fs.get('id'),
                    'type': fs.get('type'),
                    'size': fs.get('size'),
                    'codec': fs.get('codec'),
                    'bitrate': fs.get('bitrate'),
                })

            trans['filesets'] = processed_filesets
            processed.append(trans)
        return processed
