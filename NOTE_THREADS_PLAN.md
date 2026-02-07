# Note Threads Feature - Implementation Plan

**Feature**: Social platform-like commenting system for Bible study notes

**Created**: 2026-02-07

**Status**: Planning Phase

---

## **Feature Overview**

A commenting system that allows users to have threaded discussions 
on notes. Users can comment on their own private notes, and any user 
can comment on public notes, creating a social discussion platform 
around Bible study.

---

## **1. Database Schema Changes**

### **1.1 New Model: `NoteComment`**

Create a new model to represent comments in note threads:

```python
class NoteComment(models.Model):
    id = CharField(
        max_length=18, 
        primary_key=True
    )  # NCM + 15 chars
    note = ForeignKey(
        Note, 
        on_delete=CASCADE, 
        related_name='comments'
    )
    user = ForeignKey(
        User, 
        on_delete=CASCADE, 
        related_name='note_comments'
    )
    parent_comment = ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=CASCADE,
        related_name='replies'
    )
    comment_text = TextField(
        help_text="The comment content"
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']  # Chronological order
        indexes = [
            Index(fields=['note', 'created_at']),
            Index(fields=['parent_comment']),
        ]
```

**Key Design Decisions:**
- **Hierarchical structure**: `parent_comment` allows nested replies 
  (Reddit/Twitter-style threading)
- **ID format**: `NCM` prefix + 15 random characters for consistency 
  with existing ID scheme
- **Cascade deletion**: When a note is deleted, all comments are 
  deleted
- **User tracking**: Every comment is tied to a user (authenticated 
  or guest)
- **Timestamps**: Track creation and updates for comment history

---

## **2. API Endpoints**

### **2.1 Comment CRUD Operations**

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/api/v1/notes/{note_id}/comments/` | List all comments for a note | No* |
| `POST` | `/api/v1/notes/{note_id}/comments/` | Create a new comment | Yes** |
| `GET` | `/api/v1/comments/{comment_id}/` | Get a specific comment | No* |
| `PUT/PATCH` | `/api/v1/comments/{comment_id}/` | Update a comment | Yes |
| `DELETE` | `/api/v1/comments/{comment_id}/` | Delete a comment | Yes |
| `GET` | `/api/v1/comments/{comment_id}/replies/` | Get replies to a comment | No* |

\* Unauthenticated users can view comments on public notes only  
\** Unauthenticated users post as guest user

### **2.2 Query Parameters**

- `?parent_comment=null` - Get only top-level comments (no replies)
- `?parent_comment={id}` - Get replies to a specific comment
- `?user={user_id}` - Filter comments by user
- `?ordering=created_at` or `?ordering=-created_at` - Sort order

---

## **3. Access Control & Permissions**

### **3.1 Viewing Comments**

| User Type | Private Note | Public Note |
|-----------|--------------|-------------|
| **Unauthenticated** | ❌ No access | ✅ Can view all comments |
| **Authenticated (Owner)** | ✅ Can view all comments | ✅ Can view all comments |
| **Authenticated (Other)** | ❌ No access | ✅ Can view all comments |

### **3.2 Creating Comments**

| User Type | Private Note | Public Note |
|-----------|--------------|-------------|
| **Unauthenticated** | ❌ Cannot comment | ✅ Comment as guest user |
| **Authenticated (Owner)** | ✅ Can comment | ✅ Can comment |
| **Authenticated (Other)** | ❌ Cannot comment | ✅ Can comment |

### **3.3 Editing/Deleting Comments**

- Users can **only edit/delete their own comments**
- Note owner can **optionally delete any comment** on their note 
  (configurable)
- Staff users can moderate (delete) any comment

---

## **4. Implementation Steps**

### **Phase 1: Database & Models** (Est. 1-2 hours)

1. **Create `NoteComment` model** in `annotations/models.py`
   - Add ID generation function `generate_note_comment_id()`
   - Add model with all fields and relationships
   - Add `__str__` method for admin display

2. **Create and run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Register model in admin** (`annotations/admin.py`)
   - Add `NoteCommentAdmin` class
   - Enable filtering by note, user, created_at
   - Add search functionality

### **Phase 2: Serializers** (Est. 1 hour)

1. **Create `NoteCommentSerializer`** in 
   `annotations/serializers.py`
   ```python
   class NoteCommentSerializer(serializers.ModelSerializer):
       user_username = serializers.CharField(
           source='user.username', 
           read_only=True
       )
       replies_count = serializers.SerializerMethodField()
       
       class Meta:
           model = NoteComment
           fields = [
               'id', 'note', 'user', 'user_username',
               'parent_comment', 'comment_text',
               'replies_count', 'created_at', 'updated_at'
           ]
           read_only_fields = [
               'id', 'user', 'created_at', 'updated_at'
           ]
   ```

2. **Update `NoteSerializer`** to include comment count
   ```python
   comments_count = serializers.SerializerMethodField()
   
   def get_comments_count(self, obj):
       return obj.comments.count()
   ```

### **Phase 3: Views & ViewSets** (Est. 2-3 hours)

1. **Create `NoteCommentViewSet`** in `annotations/views.py`
   - Implement `get_queryset()` with permission logic
   - Implement `perform_create()` to assign user
   - Implement `perform_update()` with ownership check
   - Implement `perform_destroy()` with ownership check
   - Add custom action for nested replies

2. **Add permission checks**
   - Check if note is accessible before showing comments
   - Verify user can comment on the note
   - Validate parent_comment belongs to same note

### **Phase 4: URL Routing** (Est. 30 min)

1. **Update `annotations/urls.py`**
   ```python
   router.register(
       r'notes/(?P<note_id>[^/.]+)/comments',
       NoteCommentViewSet,
       basename='note-comments'
   )
   router.register(
       r'comments',
       NoteCommentViewSet,
       basename='comments'
   )
   ```

### **Phase 5: Testing** (Est. 2-3 hours)

1. **Manual API testing**
   - Test comment creation on public/private notes
   - Test nested replies
   - Test permission boundaries
   - Test guest user commenting

2. **Edge cases**
   - Deleting a note with comments
   - Deleting a comment with replies
   - Updating non-existent comment
   - Accessing comments on private notes

### **Phase 6: Documentation** (Est. 1 hour)

1. **Update DEVELOPER_GUIDE.md**
   - Add Note Comments section
   - Document all endpoints
   - Add example requests/responses
   - Update database schema section

2. **Add API examples**
   ```bash
   # Create a comment
   curl -X POST \
     http://localhost:8000/api/v1/notes/NOT123/comments/ \
     -H "Authorization: Token $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"comment_text": "Great insight on this verse!"}'
   
   # Reply to a comment
   curl -X POST \
     http://localhost:8000/api/v1/notes/NOT123/comments/ \
     -H "Authorization: Token $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "comment_text": "I agree!",
       "parent_comment": "NCM456"
     }'
   ```

---

## **5. Advanced Features (Optional - Future Enhancements)**

### **5.1 Comment Reactions** (Phase 2)
- Add `NoteCommentReaction` model
- Support emoji reactions (👍, ❤️, 🙏, etc.)
- Track who reacted

### **5.2 Comment Notifications** (Phase 2)
- Notify note owner of new comments
- Notify when someone replies to your comment
- Email/in-app notification system

### **5.3 Comment Moderation** (Phase 2)
- Flag inappropriate comments
- Hide/unhide comments
- Block users from commenting

### **5.4 Rich Text Comments** (Phase 3)
- Support markdown formatting
- Allow Bible verse references with auto-linking
- Support @mentions of other users

### **5.5 Comment Search** (Phase 3)
- Full-text search across comments
- Filter by date range
- Filter by user

---

## **6. Database Migration Strategy**

Since this is a new feature with no existing data:

1. **Create migration** with `NoteComment` model
2. **No data migration needed** (fresh table)
3. **Add indexes** for performance:
   - `(note_id, created_at)` - Fast comment retrieval
   - `(parent_comment_id)` - Fast reply lookup
   - `(user_id)` - User comment history

---

## **7. API Response Examples**

### **7.1 List Comments**
```json
GET /api/v1/notes/NOT123456789ABCDE/comments/

[
  {
    "id": "NCM123456789ABCDE",
    "note": "NOT123456789ABCDE",
    "user": 1,
    "user_username": "testuser",
    "parent_comment": null,
    "comment_text": "This is a great note!",
    "replies_count": 2,
    "created_at": "2026-02-07T18:00:00Z",
    "updated_at": "2026-02-07T18:00:00Z"
  },
  {
    "id": "NCM234567890BCDEF",
    "note": "NOT123456789ABCDE",
    "user": 2,
    "user_username": "john",
    "parent_comment": "NCM123456789ABCDE",
    "comment_text": "I agree!",
    "replies_count": 0,
    "created_at": "2026-02-07T18:05:00Z",
    "updated_at": "2026-02-07T18:05:00Z"
  }
]
```

### **7.2 Create Comment**
```json
POST /api/v1/notes/NOT123456789ABCDE/comments/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

{
  "comment_text": "Thanks for sharing this insight!"
}

Response (201 Created):
{
  "id": "NCM345678901CDEFG",
  "note": "NOT123456789ABCDE",
  "user": 1,
  "user_username": "testuser",
  "parent_comment": null,
  "comment_text": "Thanks for sharing this insight!",
  "replies_count": 0,
  "created_at": "2026-02-07T18:10:00Z",
  "updated_at": "2026-02-07T18:10:00Z"
}
```

---

## **8. Code Style Compliance**

Following project guidelines:
- ✅ **Python line length**: Max 79 characters (PEP 8)
- ✅ **Commit format**: `Feat: Add note threading feature`
- ✅ **Logging**: Add comprehensive logging to all viewset methods
- ✅ **Documentation**: Update DEVELOPER_GUIDE.md
- ✅ **Consistency**: Follow existing patterns from `Note` and 
  `Tag` models

---

## **9. Estimated Timeline**

| Phase | Tasks | Time Estimate |
|-------|-------|---------------|
| **Phase 1** | Models & Migrations | 1-2 hours |
| **Phase 2** | Serializers | 1 hour |
| **Phase 3** | Views & ViewSets | 2-3 hours |
| **Phase 4** | URL Routing | 30 minutes |
| **Phase 5** | Testing | 2-3 hours |
| **Phase 6** | Documentation | 1 hour |
| **Total** | | **7.5-10.5 hours** |

---

## **10. Security Considerations**

1. **Rate Limiting**: Prevent comment spam (future enhancement)
2. **Input Validation**: Sanitize comment text to prevent XSS
3. **Permission Checks**: Verify note access before allowing 
   comments
4. **Guest User Limits**: Consider limiting guest user comment 
   frequency
5. **Soft Deletes**: Optionally keep deleted comments for 
   moderation review

---

## **11. Implementation Checklist**

### **Phase 1: Database & Models**
- [ ] Create `generate_note_comment_id()` function
- [ ] Create `NoteComment` model
- [ ] Add model to `annotations/models.py`
- [ ] Create migrations
- [ ] Run migrations
- [ ] Register in admin panel
- [ ] Test model creation in Django shell

### **Phase 2: Serializers**
- [ ] Create `NoteCommentSerializer`
- [ ] Add `user_username` field
- [ ] Add `replies_count` method
- [ ] Update `NoteSerializer` with `comments_count`
- [ ] Test serializer validation

### **Phase 3: Views & ViewSets**
- [ ] Create `NoteCommentViewSet`
- [ ] Implement `get_queryset()` with permissions
- [ ] Implement `perform_create()`
- [ ] Implement `perform_update()`
- [ ] Implement `perform_destroy()`
- [ ] Add logging to all methods
- [ ] Test all CRUD operations

### **Phase 4: URL Routing**
- [ ] Add nested route for note comments
- [ ] Add standalone comments route
- [ ] Test URL patterns
- [ ] Verify routing with `python manage.py show_urls`

### **Phase 5: Testing**
- [ ] Test comment creation (authenticated)
- [ ] Test comment creation (guest user)
- [ ] Test nested replies
- [ ] Test permission boundaries
- [ ] Test comment editing
- [ ] Test comment deletion
- [ ] Test cascade deletion (note → comments)
- [ ] Test cascade deletion (comment → replies)
- [ ] Test filtering by parent_comment
- [ ] Test filtering by user

### **Phase 6: Documentation**
- [ ] Update DEVELOPER_GUIDE.md
- [ ] Add API endpoint documentation
- [ ] Add request/response examples
- [ ] Update database schema section
- [ ] Add cURL examples
- [ ] Update Table of Contents

---

## **Summary**

This plan provides a complete social commenting feature that:
- ✅ Allows threaded discussions on notes
- ✅ Respects existing privacy model (public/private notes)
- ✅ Follows Django REST Framework best practices
- ✅ Maintains consistency with existing codebase
- ✅ Provides clear API for frontend integration
- ✅ Supports both authenticated and guest users
- ✅ Includes comprehensive documentation

The implementation is modular and can be extended with reactions, 
notifications, and moderation features in future iterations.

---

## **Next Steps**

1. Review this plan with the team
2. Get approval for the design
3. Begin Phase 1 implementation
4. Create feature branch: `feature/note-threads`
5. Implement in phases with commits after each phase
6. Submit PR for review after Phase 6 completion

---

**Last Updated**: 2026-02-07
