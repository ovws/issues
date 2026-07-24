package media

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"testing"
	"time"
)

var archiveTestTime = time.Date(2026, time.July, 18, 19, 30, 45, 123000000, time.Local)

func TestLocalStoreWritesAndRejectsTraversal(t *testing.T) {
	store, err := NewLocalStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	store.now = func() time.Time { return archiveTestTime }
	key, err := store.SaveImage(context.Background(), "img_abcdefghijklmnopqrstuvwxyz", "image/jpeg", []byte("image"))
	if err != nil {
		t.Fatal(err)
	}
	store.now = func() time.Time { return archiveTestTime }
	body, err := store.Open(context.Background(), key)
	if err != nil {
		t.Fatal(err)
	}
	data, err := io.ReadAll(body)
	_ = body.Close()
	if err != nil || string(data) != "image" {
		t.Fatalf("stored image = %q, err=%v", data, err)
	}
	if _, err := store.SaveImage(context.Background(), "img_abcdefghijklmnopqrstuvwxyz", "image/jpeg", []byte("replacement")); err == nil {
		t.Fatal("existing image was overwritten")
	}
	if _, err := store.Open(context.Background(), "../outside.jpg"); err == nil {
		t.Fatal("path traversal was accepted")
	}
	if err := store.Delete(context.Background(), key); err != nil {
		t.Fatal(err)
	}
	if err := store.Delete(context.Background(), key); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("missing object delete error = %v", err)
	}
}

func TestLocalStoreRetriesTemporaryCleanupWithoutDeletingCommittedImage(t *testing.T) {
	root := t.TempDir()
	store, err := NewLocalStore(root)
	if err != nil {
		t.Fatal(err)
	}
	removeTemporary := store.removeTemporary
	removeAttempts := 0
	store.removeTemporary = func(path string) error {
		removeAttempts++
		if removeAttempts == 1 {
			return errors.New("transient cleanup failure")
		}
		return removeTemporary(path)
	}

	key, err := store.SaveImage(context.Background(), "img_cleanup_retry_0000000001", "image/png", []byte("image"))
	if err != nil {
		t.Fatal(err)
	}
	if removeAttempts != 2 {
		t.Fatalf("temporary cleanup attempts = %d, want 2", removeAttempts)
	}
	body, err := store.Open(context.Background(), key)
	if err != nil {
		t.Fatal(err)
	}
	data, readErr := io.ReadAll(body)
	_ = body.Close()
	if readErr != nil || string(data) != "image" {
		t.Fatalf("committed image = %q, err = %v", data, readErr)
	}
	temporaryFiles, err := filepath.Glob(filepath.Join(root, "2026-07-18", "photos", ".image-*"))
	if err != nil {
		t.Fatal(err)
	}
	store.now = func() time.Time { return archiveTestTime }
	if len(temporaryFiles) != 0 {
		t.Fatalf("temporary files were not cleaned: %#v", temporaryFiles)
	}
}

func TestLocalStoreCommitsStreamedVideo(t *testing.T) {
	store, err := NewLocalStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	tempPath, key, err := store.BeginVideoUpload(
		context.Background(),
		"video_stream_commit_0000000001",
		"video/mp4",
	)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(tempPath, []byte("video"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := store.CommitVideoUpload(context.Background(), tempPath, key); err != nil {
		t.Fatal(err)
	}
	body, err := store.Open(context.Background(), key)
	if err != nil {
		t.Fatal(err)
	}
	data, readErr := io.ReadAll(body)
	_ = body.Close()
	if readErr != nil || string(data) != "video" {
		t.Fatalf("committed video = %q, err = %v", data, readErr)
	}
}

func TestLocalStoreArchivesMediaByDateAndTimestamp(t *testing.T) {
	store, err := NewLocalStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	store.now = func() time.Time { return archiveTestTime }

	imageKey, err := store.SaveImage(context.Background(), "img_test", "image/png", []byte("image"))
	if err != nil {
		t.Fatal(err)
	}
	if want := "2026-07-18/photos/20260718_193045_123_img_test.png"; imageKey != want {
		t.Fatalf("image key = %q, want %q", imageKey, want)
	}

	_, videoKey, err := store.BeginVideoUpload(context.Background(), "vid_test", "video/mp4")
	if err != nil {
		t.Fatal(err)
	}
	if want := "2026-07-18/videos/20260718_193045_123_vid_test.mp4"; videoKey != want {
		t.Fatalf("video key = %q, want %q", videoKey, want)
	}
}
