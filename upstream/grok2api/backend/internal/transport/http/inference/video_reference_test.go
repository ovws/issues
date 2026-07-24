package inference

import (
	"bytes"
	"encoding/base64"
	"image"
	"image/png"
	"math/rand"
	"strings"
	"testing"
)

func TestPrepareVideoReferenceURLsCompactsInlinePNGForPersistence(t *testing.T) {
	source := image.NewNRGBA(image.Rect(0, 0, 1672, 941))
	random := rand.New(rand.NewSource(80))
	if _, err := random.Read(source.Pix); err != nil {
		t.Fatal(err)
	}
	var encoded bytes.Buffer
	if err := png.Encode(&encoded, source); err != nil {
		t.Fatal(err)
	}
	input := "data:image/png;base64," + base64.StdEncoding.EncodeToString(encoded.Bytes())
	if len(input) <= 1<<20 {
		t.Fatalf("test input must exceed persistence limit: %d", len(input))
	}

	prepared, err := prepareVideoReferenceURLs([]string{input})
	if err != nil {
		t.Fatal(err)
	}
	if len(prepared) != 1 || !strings.HasPrefix(prepared[0], "data:image/jpeg;base64,") {
		t.Fatalf("prepared reference is not JPEG data URI")
	}
	if len(prepared[0]) > videoReferenceMaxDataURILength {
		t.Fatalf("prepared data URI length = %d", len(prepared[0]))
	}
	if len(prepared[0]) >= len(input) {
		t.Fatalf("prepared data URI was not compacted: before=%d after=%d", len(input), len(prepared[0]))
	}
}

func TestPrepareVideoReferenceURLsLeavesHTTPSUntouched(t *testing.T) {
	const input = "https://example.com/reference.png"
	prepared, err := prepareVideoReferenceURLs([]string{"  " + input + "  "})
	if err != nil {
		t.Fatal(err)
	}
	if len(prepared) != 1 || prepared[0] != input {
		t.Fatalf("prepared = %#v", prepared)
	}
}

func TestPrepareVideoReferenceURLsRejectsInvalidDataURI(t *testing.T) {
	_, err := prepareVideoReferenceURLs([]string{"data:text/plain;base64,dGVzdA=="})
	if err == nil || !strings.Contains(err.Error(), "必须是图片") {
		t.Fatalf("err = %v", err)
	}
}
