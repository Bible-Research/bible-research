import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiExample
)

from .serializers import (
    UserRegistrationSerializer,
    UserSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    request=UserRegistrationSerializer,
    responses={
        201: OpenApiResponse(
            description="User registered successfully",
            examples=[
                OpenApiExample(
                    'Success Response',
                    value={
                        'user': {
                            'id': 3,
                            'username': 'newuser',
                            'email': 'user@example.com',
                            'date_joined': '2026-03-01T07:11:10Z'
                        },
                        'token': (
                            'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
                        ),
                        'message': 'User registered successfully'
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Validation error"
        )
    },
    description=(
        "Register a new user account. "
        "Email is optional. Password must be at least "
        "8 characters. Returns user data and "
        "authentication token."
    ),
    tags=['Users']
)
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


@extend_schema(
    responses={
        200: UserSerializer,
    },
    description=(
        "Retrieve the current authenticated user's "
        "information including username, email, and "
        "date joined."
    ),
    tags=['Users']
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
