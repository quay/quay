package shared

import (
	"archive/tar"
	"compress/gzip"
	"crypto/tls"
	"crypto/x509"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"path/filepath"
	"reflect"
	"strings"

	log "github.com/sirupsen/logrus"
)

// FixInterface converts a map[interface{}]interface{} into a map[string]interface{}
func FixInterface(input map[interface{}]interface{}) map[string]interface{} {
	output := make(map[string]interface{})
	for key, value := range input {
		strKey := fmt.Sprintf("%v", key)
		output[strKey] = value
	}
	return output
}

// GetFields will return the list of YAML fields in a given field group
func GetFields(fg FieldGroup) []string {

	var fieldNames []string

	// get type
	t := reflect.Indirect(reflect.ValueOf(fg)).Type()

	// Iterate over all available fields and read the tag value
	for i := 0; i < t.NumField(); i++ {
		// Get the field, returns https://golang.org/pkg/reflect/#StructField
		field := t.Field(i)

		// Get the field tag value
		yaml := field.Tag.Get("yaml")

		fieldNames = append(fieldNames, yaml)

	}

	return fieldNames
}

// LoadCerts will load certificates in a config directory.
func LoadCerts(dir string) map[string][]byte {

	// Check if dir exists
	if _, err := os.Stat(dir); os.IsNotExist(err) {
		return map[string][]byte{}
	}

	// Get filenames in directory
	certs := make(map[string][]byte)
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if info.IsDir() || strings.Contains(path, "..") || (!strings.HasSuffix(path, ".crt") && !strings.HasSuffix(path, ".cert") && !strings.HasSuffix(path, ".key") && !strings.HasSuffix(path, ".pem")) {
			return nil
		}

		data, err := ioutil.ReadFile(path)
		if err != nil {
			return err
		}

		relativePath, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}

		certs[relativePath] = data
		return nil
	})
	if err != nil {
		return map[string][]byte{}
	}

	return certs
}

// CreateArchive will create a tar file from a directory.
func CreateArchive(directory string, buf io.Writer) error {
	gw := gzip.NewWriter(buf)
	defer gw.Close()
	tw := tar.NewWriter(gw)
	defer tw.Close()

	files := []string{}
	err := filepath.Walk(directory, func(path string, info os.FileInfo, err error) error {
		if info.IsDir() {
			return nil
		}
		files = append(files, path)
		return nil
	})
	if err != nil {
		return err
	}

	for _, file := range files {
		err := addToArchive(tw, file)
		if err != nil {
			return err
		}
	}

	return nil
}

// Helper function for creation of arhive
func addToArchive(tw *tar.Writer, filename string) error {

	// Open the file which will be written into the archive
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	// Get FileInfo about our file providing file size, mode, etc.
	info, err := file.Stat()
	if err != nil {
		return err
	}

	// Create a tar Header from the FileInfo data
	header, err := tar.FileInfoHeader(info, info.Name())
	if err != nil {
		return err
	}

	header.Name = filename

	// Write file header to the tar archive
	err = tw.WriteHeader(header)
	if err != nil {
		return err
	}

	// Copy file content to tar archive
	_, err = io.Copy(tw, file)
	if err != nil {
		return err
	}

	return nil
}

// FixNumbers will convert all json.Number values to integer values
func FixNumbers(m map[string]interface{}) map[string]interface{} {
	for k, v := range m {
		_ = k
		if v, ok := v.(map[string]interface{}); ok {
			FixNumbers(v)
		}
		if v, ok := v.(float64); ok {
			m[k] = int(v)
		}
	}
	return m
}

// RemoveNullValues will remove empty values from a config.yaml. This will prevent a panic when it is unmarshalled.
func RemoveNullValues(m map[string]interface{}) map[string]interface{} {
	for k, v := range m {
		_ = k
		if v, ok := v.(map[string]interface{}); ok {
			RemoveNullValues(v)
		}
		if v == nil {
			delete(m, k)
		}
	}
	return m
}

// InterfaceArrayToStringArray converts a []interface{} to []string
func InterfaceArrayToStringArray(input []interface{}) []string {
	output := make([]string, len(input))
	for i, v := range input {
		output[i] = v.(string)
	}
	return output
}

// GetTlsConfig will build a tls config struct given a set of CA certs
func GetTlsConfig(opts Options) (*tls.Config, error) {

	rootCAs, err := x509.SystemCertPool()
	if err != nil {
		return nil, err
	}
	if rootCAs == nil {
		rootCAs = x509.NewCertPool()
	}

	for name, cert := range opts.Certificates {
		if strings.HasPrefix(name, "extra_ca_certs/") {
			if ok := rootCAs.AppendCertsFromPEM(cert); !ok {
				log.Warningf("Could not load extra ca cert file: %s. Skipping.", name)
			}
		}
	}

	return &tls.Config{RootCAs: rootCAs}, nil
}

// HasOIDCProvider will find if an OIDC provider is included in a config.yaml
func HasOIDCProvider(fullConfig map[string]interface{}) bool {

	for key, value := range fullConfig {
		if _, ok := value.(map[string]interface{}); ok {
			if strings.HasSuffix(key, "_LOGIN_CONFIG") && key != "GOOGLE_LOGIN_CONFIG" && key != "GITHUB_LOGIN_CONFIG" {
				return true
			}
		}
	}
	return false
}
