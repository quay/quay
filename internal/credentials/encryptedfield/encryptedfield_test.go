package encryptedfield

import (
	"errors"
	"testing"
)

func TestDecryptPythonVectors(t *testing.T) {
	tests := []struct {
		name      string
		secretKey string
		encrypted string
		want      string
	}{
		{name: "empty", secretKey: "test1234", encrypted: "v0$$iE+87Qefu/2i+5zC87nlUtOskypk8MUUDS/QZPs=", want: ""},
		{name: "hello world", secretKey: "test1234", encrypted: "v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==", want: "hello world"},
		{name: "hello world second nonce", secretKey: "test1234", encrypted: "v0$$9LadVsSvfAr9r1OvghSYcJqrJpv46t+U6NgLKrcFY6y2bQsASIN36g==", want: "hello world"},
		{name: "control key material", secretKey: "\x01\x02\x03\x04\x05\x06", encrypted: "v0$$2wwWX8IhUYzuh4cyMgSXF3MEVDlEhrf0CNimTghlHgCuK6E4+bLJb1xJOKxsXMs=", want: "hello world, again"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := Decrypt(tc.secretKey, tc.encrypted)
			if err != nil {
				t.Fatalf("Decrypt: %v", err)
			}
			if got != tc.want {
				t.Fatalf("got %q, want %q", got, tc.want)
			}
		})
	}
}

func TestDecryptFailures(t *testing.T) {
	tests := []struct {
		name      string
		secretKey string
		encrypted string
		wantErr   error
	}{
		{name: "empty value", secretKey: "test1234", encrypted: "", wantErr: ErrInvalidFormat},
		{name: "missing separator", secretKey: "test1234", encrypted: "somerandomvalue", wantErr: ErrInvalidFormat},
		{name: "unsupported version", secretKey: "test1234", encrypted: "v1$$abcd", wantErr: ErrUnsupportedVersion},
		{name: "invalid base64", secretKey: "test1234", encrypted: "v0$$not-base64", wantErr: ErrInvalidFormat},
		{name: "too short decoded payload", secretKey: "test1234", encrypted: "v0$$abcd", wantErr: ErrInvalidFormat},
		{name: "wrong key", secretKey: "wrong-key", encrypted: "v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==", wantErr: ErrDecrypt},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := Decrypt(tc.secretKey, tc.encrypted)
			if !errors.Is(err, tc.wantErr) {
				t.Fatalf("err = %v, want %v", err, tc.wantErr)
			}
		})
	}
}
