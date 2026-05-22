Fix security and reliability issues in image attachments

- Fix 1 (critical): add PIL magic-bytes check in upload_original so
  forged Content-Type headers cannot bypass image validation; check
  runs after size guard so oversized fakes still return 413

- Fix 2+8 (high/low): replace per-request storage.Client() with a
  module-level singleton (_get_client); cache GCP credentials via
  _get_credentials (one token refresh per expiry window); cache
  signed URLs by storage_url with TTL — eliminates N+1 IAM signBlob
  calls on list responses

- Fix 3 (high): wrap Image.objects.create in try/except in both
  NoteImageViewSet and CommentImageViewSet; call delete_original on
  failure to prevent GCS objects from being orphaned

- Fix 4 (high): signed_image_url returns None on all failure paths
  instead of the raw gs:// URI; serializer fallback updated to match

- Fix 5 (medium): change storage_url from URLField to CharField —
  URLValidator rejects gs:// URIs; add migration 0009

- Fix 6 (medium): add cors block to both GCS image buckets in
  images_storage.tf; add cors_origins variable to variables.tf

- Fix 7 (medium): add permission_classes = [IsAuthenticated] to
  ImageDestroyView so unauthenticated DELETE returns 401 explicitly

- Fix 9 (low): enforce IMAGE_MAX_PER_NOTE (10) and
  IMAGE_MAX_PER_COMMENT (5) caps before GCS upload; settings and
  .env.example updated

- Fix 10 (low): add 6 missing tests — PIL spoof at service and API
  level, unauthenticated GET/POST/DELETE, no-file POST; update
  test_owner_delete to patch _get_client instead of storage.Client

- Add Pillow>=10,<12 to requirements.txt
