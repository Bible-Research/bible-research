# Windsurf AI Rules - Bible Research API

## Critical Rules (ALWAYS Follow)

### Code Style
- **Python line length**: Maximum 79 characters (STRICT)
- **Imports**: Standard lib → Django → Third-party → Local
- **Naming**: PascalCase (classes), snake_case (functions/variables)

### Line Length Examples
```python
# ✅ GOOD
response_format = request.query_params.get(
    'response_format', 'text'
)

# ❌ BAD - Too long!
response_format = request.query_params.get('response_format', 'text')
```

### Testing
- **DO NOT** run `bundle exec rspec` (Ruby - not applicable)
- **DO** test only edited files for Python
- **DO** use test users: `testuser` / `guest`

## Project Structure

### Two Main Apps
1. **bible**: Bible data retrieval, DBT API integration
2. **annotations**: User notes, tags, hierarchical organization

### Key Files
```
bible/services/dbt/client.py  # DBT API wrapper
bible/utils/bible_books.py    # Book name mappings
annotations/models.py          # Tag, Note, NoteVerse
config.yaml                    # Secrets (gitignored)
```

## Common Patterns

### User Assignment
```python
def perform_create(self, serializer):
    if self.request.user.is_authenticated:
        serializer.save(user=self.request.user)
    else:
        guest = User.objects.get(username='guest')
        serializer.save(user=guest)
```

### Permission Checks
```python
def perform_update(self, serializer):
    if instance.user != self.request.user:
        raise PermissionDenied("Cannot update others' data")
    serializer.save()
```

### DBT API Usage
```python
from bible.services.dbt.client import DBTClient

client = DBTClient()
verses = client.get_verses(book='JHN', chapter='3')
```

## Quick Commands

```bash
# Setup
python scripts/create_test_user.py

# Database
python manage.py makemigrations
python manage.py migrate

# Testing
python manage.py test annotations  # Test specific app
```

## Git Workflow

### Commit Messages
**Format**: `Type: Capitalized message description`

**Examples**:
- ✅ `Feat: Add Vercel Analytics integration`
- ✅ `Fix: Resolve audio playback issue on Safari`
- ✅ `Docs: Update DEVELOPER_GUIDE with caching strategy`
- ❌ `feat: add analytics` (lowercase type)
- ❌ `Feat: add analytics` (lowercase message)

**Types**: Feat, Fix, Docs, Refactor, Test, Chore, Style, Perf

## Never Do
- ❌ Exceed 79 chars in Python
- ❌ Commit secrets to git
- ❌ Modify applied migrations
- ❌ Skip authentication checks
- ❌ Use raw SQL (use ORM)
- ❌ Use lowercase commit types

## Always Do
- ✅ Validate user input
- ✅ Handle API errors
- ✅ Add docstrings
- ✅ Check user permissions
- ✅ **Update DEVELOPER_GUIDE.md after significant changes**
- ✅ Use UPPERCASE commit types
- ✅ Capitalize commit messages

---

See `WINDSURF_AI_GUIDELINES.md` for complete documentation.
