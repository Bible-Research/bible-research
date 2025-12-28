# Windsurf AI Agent Guidelines - Bible Research API

## Overview

This document provides guidelines for Windsurf AI agents working on the 
Bible Research API project. Follow these guidelines to ensure consistent, 
high-quality contributions that align with project standards.

---

## Table of Contents

1. [Project Context](#project-context)
2. [Code Style & Standards](#code-style--standards)
3. [Architecture Patterns](#architecture-patterns)
4. [Database Guidelines](#database-guidelines)
5. [API Design Principles](#api-design-principles)
6. [Testing Guidelines](#testing-guidelines)
7. [Security Considerations](#security-considerations)
8. [Git Workflow](#git-workflow)
9. [Common Tasks](#common-tasks)
10. [Troubleshooting](#troubleshooting)
11. [Don'ts - Important Restrictions](#donts---important-restrictions)

---

## Project Context

### Project Purpose
This is a **Django REST API backend** for a Bible research application. 
It serves as the backend for a separate React frontend.

### Key Responsibilities
- Provide Bible verse data (text and audio) via DBT API integration
- Manage user annotations (notes and tags)
- Handle authentication and authorization
- Support multiple Bible translations

### Technology Stack
- **Framework**: Django 4.2.6 with Django REST Framework
- **Database**: PostgreSQL (production), SQLite (development)
- **External API**: Digital Bible Platform (DBT) API v4
- **Authentication**: Token-based (DRF TokenAuthentication)

---

## Code Style & Standards

### Python Style

#### Line Length
**CRITICAL**: Python lines must NOT exceed 79 characters (PEP 8)

**Good**:
```python
response_format = request.query_params.get(
    'response_format', 'text'
)

error_message = (
    f"Verse not found for '{verse_ref_data['book']} "
    f"{verse_ref_data['chapter']}:{verse_ref_data['verse']}'"
)
```

**Bad**:
```python
response_format = request.query_params.get('response_format', 'text')  # Too long!

error_message = f"Verse not found for '{verse_ref_data['book']} {verse_ref_data['chapter']}:{verse_ref_data['verse']}'"  # Too long!
```

#### Import Organization
```python
# Standard library imports
import os
import sys
from typing import Dict, Optional, Any

# Django imports
from django.db import models
from django.contrib.auth import get_user_model

# Third-party imports
from rest_framework import serializers, viewsets

# Local imports
from .models import Tag, Note
from bible.models import Verse
```

#### Docstrings
Use triple-quoted docstrings for classes and functions:
```python
def get_verses(self, book: str, chapter: str, **kwargs):
    """
    Get verses for a specific chapter.

    Args:
        book: Book ID (e.g., 'JHN')
        chapter: Chapter number
        **kwargs: Additional query parameters

    Returns:
        Dictionary with verse data
    """
```

#### Naming Conventions
- **Classes**: `PascalCase` (e.g., `BiblePassageView`, `NoteSerializer`)
- **Functions/Methods**: `snake_case` (e.g., `get_verses`, `create_note`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_LENGTH`, `DEFAULT_TRANSLATION`)
- **Variables**: `snake_case` (e.g., `verse_count`, `user_notes`)

---

## Architecture Patterns

### Django Apps Structure

The project has two main apps:

#### 1. `bible` App
**Purpose**: Bible data retrieval and verse management

**Components**:
- `models.py`: `Verse` model only
- `views.py`: `BiblePassageView` for fetching passages
- `serializers.py`: `BiblePassageSerializer` with DBT integration
- `services/dbt/client.py`: DBT API client wrapper
- `utils/bible_books.py`: Book name mappings

**When to modify**: Adding new Bible-related features, translations, 
or verse retrieval methods

#### 2. `annotations` App
**Purpose**: User-generated content (notes and tags)

**Components**:
- `models.py`: `Tag`, `Note`, `NoteVerse` models
- `views.py`: `TagViewSet`, `NoteViewSet` for CRUD operations
- `serializers.py`: Serializers with nested relationships
- `admin.py`: Django admin configuration

**When to modify**: Adding features related to user notes, tags, 
or annotations

### ViewSet vs APIView

**Use ViewSet** (for models with full CRUD):
```python
class TagViewSet(viewsets.ModelViewSet):
    """Provides list, create, retrieve, update, destroy actions"""
    serializer_class = TagSerializer
    
    def get_queryset(self):
        # Custom filtering logic
        pass
```

**Use APIView** (for custom endpoints):
```python
class BiblePassageView(APIView):
    """Custom endpoint with specific logic"""
    
    def get(self, request, format=None):
        # Custom retrieval logic
        pass
```

### Serializer Patterns

#### Read-Write Field Separation
```python
class NoteSerializer(serializers.ModelSerializer):
    # Write-only field (accepts IDs)
    tag = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        write_only=True
    )
    
    # Read-only field (returns full object)
    tag_detail = TagSerializer(source='tag', read_only=True)
```

#### Custom Representation
```python
def to_representation(self, instance):
    """Override to add computed fields or nested data"""
    representation = super().to_representation(instance)
    
    # Add verse text from DBT API
    representation['verses'] = self._get_verses_with_text(instance)
    
    return representation
```

---

## Database Guidelines

### Model ID Generation

All models use custom ID generation with prefixes:

```python
def generate_tag_id():
    return f"TAG{str(uuid.uuid4()).upper().replace('-', '')[:15]}"

class Tag(models.Model):
    id = models.CharField(
        max_length=18,
        default=generate_tag_id,
        primary_key=True,
        editable=False,
        help_text="Unique identifier for the tag."
    )
```

**ID Prefixes**:
- `VER` - Verse
- `TAG` - Tag
- `NOT` - Note
- `NVE` - NoteVerse

### Foreign Key Patterns

**CASCADE**: Delete related objects when parent is deleted
```python
user = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    related_name='tags'
)
```

**PROTECT**: Prevent deletion if related objects exist
```python
verse = models.ForeignKey(
    Verse,
    on_delete=models.PROTECT  # Can't delete verses with notes
)
```

### Many-to-Many Relationships

Use explicit `through` model for additional fields:
```python
class Note(models.Model):
    verses = models.ManyToManyField(
        Verse,
        through='NoteVerse',
        related_name='notes'
    )

class NoteVerse(models.Model):
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    verse = models.ForeignKey(Verse, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Migrations

**Always create migrations after model changes**:
```bash
python manage.py makemigrations
python manage.py migrate
```

**Check migration SQL before applying**:
```bash
python manage.py sqlmigrate annotations 0001
```

---

## API Design Principles

### URL Patterns

**RESTful conventions**:
```python
# Good - RESTful
urlpatterns = [
    path('tags/', TagViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('tags/<pk>/', TagViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy'
    })),
]

# Better - Use routers for ViewSets
router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tag')
urlpatterns = [
    path('', include(router.urls)),
]
```

### Query Parameters

**Use clear, descriptive parameter names**:
```python
# Good
GET /api/v1/bible/?passage=John+3&translation=ENGESV&response_format=text

# Bad
GET /api/v1/bible/?p=John+3&t=ENGESV&f=text
```

### Response Format

**Consistent structure**:
```python
# Success response
{
    "id": "NOT123...",
    "note_text": "...",
    "verses": [...],
    "created_at": "2025-12-28T03:51:55Z"
}

# Error response
{
    "error": "Passage parameter is required. Example: ?passage=John+3:16"
}
```

### Filtering

**Support common filtering patterns**:
```python
def get_queryset(self):
    queryset = Note.objects.all()
    
    # Filter by tag
    tag_id = self.request.query_params.get('tag_id')
    if tag_id:
        queryset = queryset.filter(tag_id=tag_id)
    
    # Filter by public status
    public = self.request.query_params.get('public')
    if public == 'true':
        queryset = queryset.filter(
            Q(user=self.request.user) | Q(public=True)
        )
    
    return queryset
```

---

## Testing Guidelines

### Test User Setup

**IMPORTANT**: Tests should use the test user accounts

```python
from django.contrib.auth import get_user_model

User = get_user_model()

# In tests
test_user = User.objects.get(username='testuser')
guest_user = User.objects.get(username='guest')
```

### Running Tests

**DO NOT run full test suite** if it takes too long:
```bash
# Good - Test specific file
python manage.py test annotations.tests.TestNoteViewSet

# Good - Test specific app
python manage.py test annotations

# Avoid - Full suite (if slow)
# python manage.py test
```

### Test Structure

```python
from rest_framework.test import APITestCase
from rest_framework import status

class TestNoteViewSet(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_note(self):
        """Test note creation"""
        data = {
            'note_text': 'Test note',
            'verse_references': [
                {'book': 'John', 'chapter': 3, 'verse': 16}
            ]
        }
        response = self.client.post('/api/v1/notes/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

---

## Security Considerations

### Authentication

**Always check user authentication in ViewSets**:
```python
def perform_create(self, serializer):
    """Assign current user to created object"""
    if self.request.user.is_authenticated:
        serializer.save(user=self.request.user)
    else:
        # Use guest user for unauthenticated requests
        guest_user = User.objects.get(username='guest')
        serializer.save(user=guest_user)
```

### Authorization

**Ensure users can only modify their own data**:
```python
def perform_update(self, serializer):
    """Prevent users from updating others' data"""
    instance = serializer.instance
    if (self.request.user.is_authenticated and
            instance.user != self.request.user):
        raise PermissionDenied(
            "You do not have permission to update this note."
        )
    serializer.save()
```

### Input Validation

**Validate all user input**:
```python
def validate_verse_references(self, value):
    """Ensure verse references are valid"""
    if not value:
        raise serializers.ValidationError(
            "At least one verse reference is required."
        )
    
    for verse_ref in value:
        if verse_ref['chapter'] < 1:
            raise serializers.ValidationError(
                "Chapter must be a positive number."
            )
    
    return value
```

### Sensitive Data

**NEVER commit sensitive data**:
- API keys go in `config.yaml` (gitignored)
- Use `config_template.yaml` for examples
- Database credentials in `config.yaml`
- Secret key in `config.yaml`

---

## Git Workflow

### Commit Messages

Follow conventional commits with **UPPERCASE type and capitalized 
message**:
- `Feat: Add new feature`
- `Fix: Resolve bug`
- `Docs: Update documentation`
- `Refactor: Restructure code`
- `Test: Add tests`
- `Chore: Update dependencies`

**Format**: `Type: Capitalized message description`

**Examples**:
- ✅ `Feat: Add Vercel Analytics integration`
- ✅ `Fix: Resolve audio playback issue on Safari`
- ✅ `Docs: Update DEVELOPER_GUIDE with caching strategy`
- ❌ `feat: add analytics` (lowercase - incorrect)
- ❌ `Feat: add analytics` (message not capitalized - incorrect)

### Commit Message Types

- **Feat**: New feature or functionality
- **Fix**: Bug fix or error correction
- **Docs**: Documentation changes only
- **Refactor**: Code restructuring without changing behavior
- **Test**: Adding or updating tests
- **Chore**: Maintenance tasks (dependencies, config, etc.)
- **Style**: Code formatting, whitespace, etc.
- **Perf**: Performance improvements

### Best Practices

1. **Keep commits atomic**: One logical change per commit
2. **Write descriptive messages**: Explain what and why, not how
3. **Reference issues**: Include issue numbers when applicable
   - Example: `Fix: Resolve note deletion cascade issue (#42)`
4. **Use present tense**: "Add feature" not "Added feature"
5. **Keep first line under 72 characters**: For better git log display
6. **Update documentation**: Always update `DEVELOPER_GUIDE.md` after 
   significant logic changes

### Branch Naming

**Format**: `type/short-description`

**Examples**:
- `feat/verse-highlighting`
- `fix/audio-playback-safari`
- `docs/api-documentation`
- `refactor/serializer-cleanup`

---

## Common Tasks

### Updating Documentation

**IMPORTANT**: After making significant logic changes, always update 
`DEVELOPER_GUIDE.md`

**When to update**:
- Adding new API endpoints
- Changing API request/response formats
- Adding new models or fields
- Modifying authentication/authorization logic
- Adding new features or functionalities
- Changing database schema
- Updating external API integrations

**What to update in DEVELOPER_GUIDE.md**:

1. **API Endpoints section**: Add/update endpoint documentation
   ```markdown
   #### New Endpoint Name
   ```
   GET /api/v1/new-endpoint/
   Authorization: Token <your-token>
   ```
   
   **Response**:
   ```json
   {
     "field": "value"
   }
   ```
   ```

2. **Database Schema section**: Update model definitions
   ```markdown
   ### ModelName Model
   ```python
   class ModelName(models.Model):
       new_field = CharField(max_length=100)
   ```
   ```

3. **Core Functionalities section**: Document new features

4. **Common Issues section**: Add troubleshooting for new features

**Example commit with documentation**:
```bash
# Make code changes
git add bible/views.py bible/serializers.py

# Update documentation
git add DEVELOPER_GUIDE.md

# Commit with both changes
git commit -m "Feat: Add verse search endpoint

- Add search view and serializer
- Update DEVELOPER_GUIDE.md with new endpoint documentation"
```

### Adding a New Model Field

1. **Update the model**:
```python
class Note(models.Model):
    # ... existing fields ...
    is_favorite = models.BooleanField(default=False)  # New field
```

2. **Create and apply migration**:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Update serializer**:
```python
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = [
            'id', 'note_text', 'is_favorite',  # Add new field
            'created_at', 'updated_at'
        ]
```

4. **Update API documentation** in `DEVELOPER_GUIDE.md`

### Adding a New API Endpoint

1. **Create view**:
```python
class FavoriteNotesView(APIView):
    """Get user's favorite notes"""
    
    def get(self, request):
        notes = Note.objects.filter(
            user=request.user,
            is_favorite=True
        )
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data)
```

2. **Add URL pattern**:
```python
urlpatterns = [
    path('notes/favorites/', FavoriteNotesView.as_view()),
]
```

3. **Document in `DEVELOPER_GUIDE.md`**

### Integrating a New Bible Translation

1. **Find translation code** in DBT API documentation

2. **Add to book mappings** if needed:
```python
# bible/utils/bible_books.py
AUDIO_BIBLE_MAPPINGS = {
    'ENGESV': {
        '1DA': 'ENGESVN1DA',
        '2DA': 'ENGESVN2DA',
    },
    'ENGNIV': {  # New translation
        '1DA': 'ENGNIVN1DA',
        '2DA': 'ENGNIVN2DA',
    }
}
```

3. **Test with API**:
```bash
curl "http://localhost:8000/api/v1/bible/?passage=John+3&translation=ENGNIV"
```

### Working with DBT API

**Use the DBTClient wrapper**:
```python
from bible.services.dbt.client import DBTClient

client = DBTClient()

# Get verses
verses = client.get_verses(
    book='JHN',
    chapter='3',
    bible_id='ENGESV',
    verse_start=16,
    verse_end=17
)

# Search
results = client.search(
    bible_id='ENGESV',
    query='love'
)
```

**Handle API errors**:
```python
try:
    verses = client.get_verses(book, chapter, bible_id)
except Exception as e:
    logger.error(f"DBT API error: {str(e)}")
    return Response(
        {"error": "Failed to fetch verses"},
        status=status.HTTP_503_SERVICE_UNAVAILABLE
    )
```

---

## Troubleshooting

### Common Issues

#### "DBT_KEY not found in settings"
**Cause**: Missing or incorrect `config.yaml`
**Solution**: 
```bash
cp config_template.yaml config.yaml
# Edit config.yaml and add your DBT_KEY
```

#### "Verse not found" when creating note
**Cause**: Verse doesn't exist in database
**Solution**:
```bash
python manage.py import_esv_verses
# Or add verse manually:
python scripts/add_verse.py
```

#### "Guest user doesn't exist"
**Cause**: Test users not created
**Solution**:
```bash
python scripts/create_test_user.py
```

#### Migration conflicts
**Cause**: Multiple migration files for same change
**Solution**:
```bash
# Delete conflicting migration files
# Recreate migrations
python manage.py makemigrations
```

### Debugging Tips

**Enable verbose logging**:
```python
import logging
logger = logging.getLogger(__name__)

logger.debug(f"Verse data: {verse_data}")
logger.info(f"User {user.username} created note")
logger.error(f"Failed to fetch verses: {str(e)}")
```

**Use Django shell for testing**:
```bash
python manage.py shell
>>> from annotations.models import Note, Tag
>>> Note.objects.filter(user__username='testuser')
>>> Tag.objects.filter(parent_tag__isnull=True)
```

**Check database state**:
```bash
python manage.py dbshell
SELECT * FROM annotations_note LIMIT 5;
```

---

## Don'ts - Important Restrictions

### ❌ NEVER Do These

1. **Don't exceed 79 characters per line in Python files**
   - This is a hard requirement from user rules
   - Break long lines appropriately

2. **Don't run `bundle exec rspec` for Ruby projects**
   - Not applicable to this Python project, but noted in user rules

3. **Don't commit sensitive data**
   - No API keys in code
   - No passwords in code
   - No database credentials in code
   - Use `config.yaml` (gitignored)

4. **Don't modify migrations after they're applied**
   - Create new migrations instead
   - Never edit existing migration files

5. **Don't bypass authentication checks**
   - Always validate user permissions
   - Use `perform_create`, `perform_update`, `perform_destroy`

6. **Don't use raw SQL queries**
   - Use Django ORM
   - Exception: Complex queries where ORM is insufficient

7. **Don't create circular imports**
   - Keep imports organized
   - Use `get_user_model()` instead of importing User directly

8. **Don't hardcode configuration**
   - Use `settings.py` for configuration
   - Use `config.yaml` for secrets

9. **Don't ignore error handling**
   - Always handle external API failures
   - Provide meaningful error messages

10. **Don't skip input validation**
    - Validate all user input in serializers
    - Check for edge cases

### ⚠️ Be Careful With

1. **Database queries in loops**
   - Use `select_related()` and `prefetch_related()`
   - Avoid N+1 query problems

2. **External API calls**
   - Always handle timeouts
   - Implement retry logic if needed
   - Cache responses when appropriate

3. **Deleting data**
   - Use `on_delete=models.PROTECT` for critical relationships
   - Implement soft deletes if needed

4. **Changing model field types**
   - May require data migration
   - Test thoroughly before applying

---

## Best Practices

### ✅ Always Do These

1. **Write descriptive docstrings**
   - Explain what the function does
   - Document parameters and return values

2. **Use type hints**
   ```python
   def get_verses(
       self,
       book: str,
       chapter: str,
       bible_id: str = "ENGESV"
   ) -> Dict[str, Any]:
   ```

3. **Keep functions focused**
   - One function, one responsibility
   - Extract complex logic into helper functions

4. **Use meaningful variable names**
   ```python
   # Good
   verse_references = data.get('verse_references', [])
   
   # Bad
   vr = data.get('vr', [])
   ```

5. **Add helpful comments**
   ```python
   # Convert book name to DBT book ID (e.g., "John" -> "JHN")
   book_id = get_dbt_book_id(book_name)
   ```

6. **Test edge cases**
   - Empty inputs
   - Invalid data
   - Unauthenticated users
   - Missing related objects

7. **Keep serializers clean**
   - Separate read and write logic
   - Use custom methods for complex transformations

8. **Log important events**
   - User actions
   - API calls
   - Errors and exceptions

9. **Update DEVELOPER_GUIDE.md after significant changes**
   - New API endpoints
   - Model changes
   - New features
   - Authentication/authorization changes

---

## Quick Reference

### File Locations

```
bible_research/
├── bible/
│   ├── models.py              # Verse model
│   ├── views.py               # BiblePassageView
│   ├── serializers.py         # BiblePassageSerializer
│   ├── services/dbt/client.py # DBT API client
│   └── utils/bible_books.py   # Book mappings
├── annotations/
│   ├── models.py              # Tag, Note, NoteVerse
│   ├── views.py               # TagViewSet, NoteViewSet
│   └── serializers.py         # Tag/Note serializers
├── bible_research/
│   ├── settings.py            # Django settings
│   ├── urls.py                # URL routing
│   └── authentication.py      # Custom auth classes
├── scripts/
│   └── create_test_user.py    # User creation script
├── config.yaml                # Configuration (gitignored)
└── config_template.yaml       # Configuration template
```

### Useful Commands

```bash
# Development
python manage.py runserver
python manage.py shell
python manage.py dbshell

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py import_esv_verses

# Users
python scripts/create_test_user.py

# Testing
python manage.py test annotations
python manage.py test bible

# Deployment
python manage.py collectstatic
```

### Key Models

```python
# Verse
Verse.objects.get(book='John', chapter=3, verse=16)

# Tag
Tag.objects.filter(user=user, parent_tag__isnull=True)

# Note
Note.objects.filter(user=user, public=True)

# User
User.objects.get(username='testuser')
```

---

## Checklist for New Features

Before submitting code, ensure:

- [ ] Code follows 79-character line limit
- [ ] All imports are organized correctly
- [ ] Docstrings are added for new functions/classes
- [ ] Type hints are used where appropriate
- [ ] Input validation is implemented
- [ ] Error handling is in place
- [ ] Authentication/authorization checks are correct
- [ ] Database migrations are created and tested
- [ ] API endpoints are RESTful
- [ ] Tests are written (if applicable)
- [ ] **DEVELOPER_GUIDE.md is updated with changes**
- [ ] No sensitive data is committed
- [ ] Logging is added for important events
- [ ] Code is tested locally
- [ ] Commit message follows format: `Type: Capitalized message`

---

## Additional Resources

- **Django Docs**: https://docs.djangoproject.com/
- **DRF Docs**: https://www.django-rest-framework.org/
- **DBT API**: https://www.faithcomesbyhearing.com/bible-brain/api-reference
- **PEP 8**: https://pep8.org/
- **Developer Guide**: See `DEVELOPER_GUIDE.md` in this repository

---

**Last Updated**: 2025-12-28

**Note**: These guidelines are living documents. Update them as the 
project evolves and new patterns emerge.
