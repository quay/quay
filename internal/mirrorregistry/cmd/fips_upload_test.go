package cmd

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"

	"github.com/distribution/distribution/v3/configuration"
	"github.com/distribution/distribution/v3/registry/handlers"
	_ "github.com/distribution/distribution/v3/registry/storage/driver/filesystem"
)

// TestChunkedUploadOffsetMismatch reproduces the bug that causes HTTP 416
// "invalid content range" errors when the distribution registry is built
// with Red Hat's FIPS-enabled Go compiler (golang-fips).
//
// Root cause: blobWriter.Close() calls storeHashState(), which tries to
// marshal the SHA-256 hash state via encoding.BinaryMarshaler. Under
// golang-fips, the OpenSSL-backed hash implements the interface at the
// type level but MarshalBinary() returns an error ("hash state is not
// marshallable"). Close() treats this as a fatal error and returns early
// WITHOUT flushing the fileWriter's bufio buffer. The state token then
// records an Offset that includes buffered (unflushed) bytes, while the
// actual file on disk is smaller. On the next request, the offset check
// fails → HTTP 416.
//
// This test verifies the upload flow works correctly under normal (non-FIPS)
// conditions. Under FIPS with golang-fips, the PATCH step would produce a
// state token whose offset exceeds the file size, and the PUT step would
// fail with 416.
//
// Building with -tags=noresumabledigest fixes the issue by replacing
// storeHashState with a noop that returns errResumableDigestNotAvailable,
// which Close() handles correctly (always flushes the buffer).
func TestChunkedUploadOffsetMismatch(t *testing.T) {
	dir := t.TempDir()

	cfg := &configuration.Configuration{
		Storage: configuration.Storage{
			"filesystem": configuration.Parameters{
				"rootdirectory": dir,
			},
			"delete": configuration.Parameters{
				"enabled": true,
			},
		},
	}
	cfg.HTTP.Addr = "127.0.0.1:0"
	cfg.HTTP.Secret = "test-secret-for-hmac"

	app := handlers.NewApp(t.Context(), cfg)
	ts := httptest.NewServer(app)
	defer ts.Close()

	repo := "test/fips-upload"

	// Step 1: POST to start a new upload
	postURL := fmt.Sprintf("%s/v2/%s/blobs/uploads/", ts.URL, repo)
	postReq, err := http.NewRequestWithContext(t.Context(), http.MethodPost, postURL, http.NoBody)
	if err != nil {
		t.Fatalf("POST request creation failed: %v", err)
	}
	resp, err := http.DefaultClient.Do(postReq)
	if err != nil {
		t.Fatalf("POST failed: %v", err)
	}
	resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("POST: expected 202, got %d", resp.StatusCode)
	}

	uploadURL := resp.Header.Get("Location")
	if uploadURL == "" {
		t.Fatal("POST: no Location header")
	}
	if strings.HasPrefix(uploadURL, "/") {
		uploadURL = ts.URL + uploadURL
	}

	t.Logf("Upload URL: %s", uploadURL)

	// Step 2: PATCH to send chunk data
	// Using 8KB — larger than bufio's default 4KB buffer so some data
	// gets flushed and some stays buffered. Under FIPS (golang-fips),
	// Close() skips the flush, leaving the buffered bytes on disk.
	chunkData := bytes.Repeat([]byte("A"), 8192)

	patchReq, err := http.NewRequestWithContext(t.Context(), http.MethodPatch, uploadURL, bytes.NewReader(chunkData))
	if err != nil {
		t.Fatalf("PATCH request creation failed: %v", err)
	}
	patchReq.Header.Set("Content-Type", "application/octet-stream")
	patchReq.Header.Set("Content-Range", fmt.Sprintf("0-%d", len(chunkData)-1))
	patchReq.Header.Set("Content-Length", fmt.Sprintf("%d", len(chunkData)))

	resp, err = http.DefaultClient.Do(patchReq)
	if err != nil {
		t.Fatalf("PATCH failed: %v", err)
	}
	body, _ := io.ReadAll(resp.Body)
	resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		t.Fatalf("PATCH: expected 202, got %d; body: %s", resp.StatusCode, body)
	}

	patchLocation := resp.Header.Get("Location")
	if patchLocation == "" {
		t.Fatal("PATCH: no Location header")
	}
	if strings.HasPrefix(patchLocation, "/") {
		patchLocation = ts.URL + patchLocation
	}

	rangeHeader := resp.Header.Get("Range")
	t.Logf("PATCH response Range: %s", rangeHeader)

	expectedRange := fmt.Sprintf("0-%d", len(chunkData)-1)
	if rangeHeader != expectedRange {
		t.Errorf("PATCH Range: expected %q, got %q — offset mismatch indicates unflushed buffer (FIPS bug)", expectedRange, rangeHeader)
	}

	// Step 3: PUT to finalize
	// Under FIPS with golang-fips, this fails with 416 because the state
	// token's offset (from PATCH) doesn't match the file on disk.
	digest := fmt.Sprintf("sha256:%x", sha256.Sum256(chunkData))

	putURL, err := url.Parse(patchLocation)
	if err != nil {
		t.Fatalf("Failed to parse PATCH location: %v", err)
	}
	q := putURL.Query()
	q.Set("digest", digest)
	putURL.RawQuery = q.Encode()

	putReq, err := http.NewRequestWithContext(t.Context(), http.MethodPut, putURL.String(), http.NoBody)
	if err != nil {
		t.Fatalf("PUT request creation failed: %v", err)
	}

	resp, err = http.DefaultClient.Do(putReq)
	if err != nil {
		t.Fatalf("PUT failed: %v", err)
	}
	body, _ = io.ReadAll(resp.Body)
	resp.Body.Close()

	if resp.StatusCode == http.StatusRequestedRangeNotSatisfiable {
		var errResp struct {
			Errors []struct {
				Code    string `json:"code"`
				Message string `json:"message"`
			} `json:"errors"`
		}
		if err := json.Unmarshal(body, &errResp); err == nil {
			for _, e := range errResp.Errors {
				if e.Code == "RANGE_INVALID" {
					t.Fatalf("PUT got 416 RANGE_INVALID: %s — "+
						"This is the FIPS bug! The state token offset doesn't match "+
						"the file on disk because Close() didn't flush the buffer. "+
						"Build with -tags=noresumabledigest to fix.", e.Message)
				}
			}
		}
		t.Fatalf("PUT: got 416; body: %s", body)
	}

	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("PUT: expected 201, got %d; body: %s", resp.StatusCode, body)
	}

	t.Log("Chunked upload succeeded — no offset mismatch")
}
