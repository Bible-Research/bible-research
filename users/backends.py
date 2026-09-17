"""
Custom authentication backend for case-insensitive username
authentication.
"""
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveAuthBackend(ModelBackend):
    """
    Authentication backend that allows users to log in with
    username in any case.

    For example, if a user registered as 'JohnDoe', they can
    log in with 'johndoe', 'JOHNDOE', 'JohnDoe', etc.
    """

    def authenticate(
        self, request, username=None, password=None, **kwargs
    ):
        """
        Authenticate user with case-insensitive username lookup.

        Args:
            request: The HTTP request object
            username: Username provided by user (any case)
            password: Password provided by user
            **kwargs: Additional keyword arguments

        Returns:
            User object if authentication succeeds, None otherwise
        """
        if username is None or password is None:
            return None

        try:
            # Case-insensitive username lookup
            user = User.objects.get(
                username__iexact=username
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce
            # the timing difference between an existing and a
            # nonexistent user
            User().set_password(password)
            return None

        # Check password
        if user.check_password(password):
            return user

        return None
