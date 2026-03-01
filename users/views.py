import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

from .serializers import (
    UserRegistrationSerializer,
    UserSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user account.

    Accepts username, email, password, and password_confirm.
    Returns the created user data and authentication token.
    """
    logger.info(
        f"Registration attempt for username: "
        f"{request.data.get('username', 'N/A')}"
    )

    serializer = UserRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        # Create authentication token for the new user
        token, created = Token.objects.get_or_create(user=user)

        logger.info(
            f"User '{user.username}' registered successfully"
        )

        return Response(
            {
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': (
                    'User registered successfully'
                )
            },
            status=status.HTTP_201_CREATED
        )

    logger.warning(
        f"Registration failed: {serializer.errors}"
    )
    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get the current authenticated user's information.
    """
    logger.info(
        f"Current user request for: {request.user.username}"
    )
    serializer = UserSerializer(request.user)
    return Response(serializer.data)
