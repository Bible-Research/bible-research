import os
from google.cloud import secretmanager


def get_secret(secret_id, version_id="latest"):
    """
    Get a secret from Google Secret Manager.

    Args:
        secret_id: The ID of the secret to retrieve.
        version_id: The version of the secret (default is 'latest').

    Returns:
        The secret value as a string.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")