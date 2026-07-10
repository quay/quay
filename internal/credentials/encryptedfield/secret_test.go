package encryptedfield

import (
	"bytes"
	"errors"
	"testing"
)

func TestConvertSecretKey(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		prefix  []byte
		wantErr error
	}{
		{name: "plain string", input: "test1234", prefix: []byte("test1234")},
		{name: "zero integer", input: "0", prefix: []byte{0x00, 0x00, 0x00, 0x00}},
		{name: "byte integer", input: "255", prefix: []byte{0xff, 0xff, 0xff, 0xff}},
		{name: "odd hex integer fallback", input: "256", prefix: []byte("2562")},
		{name: "latin one rune", input: "é", prefix: []byte{0xe9, 0xe9, 0xe9, 0xe9}},
		{name: "zero uuid", input: "00000000-0000-0000-0000-000000000000", prefix: []byte{0x00, 0x00, 0x00, 0x00}},
		{name: "empty", input: "", wantErr: ErrInvalidKey},
		{name: "above byte rune", input: "😇", wantErr: ErrInvalidKey},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := ConvertSecretKey(tc.input)
			if tc.wantErr != nil {
				if !errors.Is(err, tc.wantErr) {
					t.Fatalf("err = %v, want %v", err, tc.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("ConvertSecretKey: %v", err)
			}
			if len(got) != 32 {
				t.Fatalf("len = %d, want 32", len(got))
			}
			if !bytes.Equal(got[:len(tc.prefix)], tc.prefix) {
				t.Fatalf("prefix = %x, want %x", got[:len(tc.prefix)], tc.prefix)
			}
		})
	}
}
