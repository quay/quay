package editor

import (
	"archive/tar"
	"bytes"
	"fmt"
	"io/ioutil"
	"log"
	"mime"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"

	auth "github.com/abbot/go-http-auth"
	bcrypt "golang.org/x/crypto/bcrypt"
	"gopkg.in/yaml.v2"

	jsoniter "github.com/json-iterator/go"
	config "github.com/quay/config-tool/pkg/lib/config"
	shared "github.com/quay/config-tool/pkg/lib/shared"
)

const port = 8080
const staticContentPath = "pkg/lib/editor/static"
const editorUsername = "quayconfig"

func handler(operatorEndpoint string) func(w http.ResponseWriter, r *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" {
			p := staticContentPath + "/index.html"

			if len(operatorEndpoint) > 0 {
				http.SetCookie(w, &http.Cookie{Name: "QuayOperatorEndpoint", Value: operatorEndpoint})
			}

			http.ServeFile(w, r, p)
			return
		}

		w.WriteHeader(404)
	}
}

// commitToOperator calls API endpoint on Quay Operator to create a new `Secret`.
func commitToOperator(configPath, operatorEndpoint string) func(w http.ResponseWriter, r *http.Request) {
	namespace := os.Getenv("MY_POD_NAMESPACE")
	if namespace == "" {
		panic("missing 'MY_POD_NAMESPACE'")
	}
	podName := os.Getenv("MY_POD_NAME")
	if podName == "" {
		panic("missing 'MY_POD_NAME'")
	}
	quayRegistryName := strings.Split(podName, "-quay-config-editor")[0]

	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			w.WriteHeader(405)
			return
		}

		var conf map[string]interface{}
		err := yaml.NewDecoder(r.Body).Decode(&conf)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		for name, cert := range shared.LoadCerts(configPath) {
			certStore[name] = cert
		}

		// TODO: Define struct type for this with correct `yaml` tags
		preSecret := map[string]interface{}{
			// FIXME(alecmerdler): Need to figure out which `QuayRegistry` we just re-configured in order to change `spec.configBundleSecret`...
			"quayRegistryName": quayRegistryName,
			"namespace":        namespace,
			"config.yaml":      conf,
			"certs":            certStore,
		}

		var json = jsoniter.ConfigCompatibleWithStandardLibrary
		js, err := json.Marshal(preSecret)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// FIXME: Currently hardcoding
		req, err := http.NewRequest("POST", operatorEndpoint+"/reconfigure", bytes.NewBuffer(js))
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		req.Header.Set("Content-Type", "application/json")
		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		defer resp.Body.Close()

		w.Header().Add("Content-Type", "application/json")
		w.Write(js)
	}
}

func downloadConfig(configPath string) func(http.ResponseWriter, *http.Request) {

	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			w.WriteHeader(405)
			return
		}

		var conf map[string]interface{}
		err := yaml.NewDecoder(r.Body).Decode(&conf)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		for name, cert := range shared.LoadCerts(configPath) {
			certStore[name] = cert
		}

		files := make(map[string][]byte)
		files["config.yaml"], err = yaml.Marshal(conf)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		for name, contents := range certStore {
			files[name] = contents
		}

		var buf bytes.Buffer
		tw := tar.NewWriter(&buf)
		hdr := &tar.Header{
			Name:     "extra_ca_certs/",
			Typeflag: tar.TypeDir,
			Mode:     0777,
		}
		if err := tw.WriteHeader(hdr); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		for name, contents := range files {
			hdr := &tar.Header{
				Name: name,
				Mode: 0777,
				Size: int64(len(contents)),
			}
			if err := tw.WriteHeader(hdr); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			if _, err := tw.Write(contents); err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
		}
		tw.Close()

		w.Header().Set("Content-type", "application/zip")
		w.Header().Set("Content-Disposition", "attachment; filename=quay-config.tar.gz")
		w.Write(buf.Bytes())
	}

}

// post request to validate config with certs
func configValidator(configPath string) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {

		if r.Method != "POST" {
			w.WriteHeader(405)
			return
		}

		var c map[string]interface{}
		err := yaml.NewDecoder(r.Body).Decode(&c)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		loaded, err := config.NewConfig(c)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		for name, cert := range shared.LoadCerts(configPath) {
			certStore[name] = cert
		}

		opts := shared.Options{
			Mode:         "online",
			Certificates: certStore,
		}

		errors := loaded.Validate(opts)

		var json = jsoniter.ConfigCompatibleWithStandardLibrary
		js, err := json.Marshal(errors)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Add("Content-Type", "application/json")
		w.Write(js)
	}
}

func configHandler(configPath string) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			w.WriteHeader(405)
			return
		}

		// Read config file
		configFilePath := path.Join(configPath, "config.yaml")
		configBytes, err := ioutil.ReadFile(configFilePath)
		if err != nil {
			http.Error(w, err.Error(), http.StatusNotFound)
			return
		}

		// Load config into struct
		var conf map[string]interface{}
		if err = yaml.Unmarshal(configBytes, &conf); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Get filenames in directory
		var certs []string
		err = filepath.Walk(configPath, func(path string, info os.FileInfo, err error) error {
			if info.IsDir() {
				return nil
			}
			certs = append(certs, path)
			return nil
		})

		// Build response
		resp := map[string]interface{}{
			"config.yaml": conf,
			"certs":       certs,
		}
		var json = jsoniter.ConfigCompatibleWithStandardLibrary
		js, err := json.Marshal(resp)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		w.Header().Add("Content-Type", "application/json")
		w.Write(js)
	}
}

func certificateHandler(configDir string) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case "PUT":
			err := r.ParseMultipartForm(10 << 20)
			if err != nil {
				fmt.Printf("error parsing request body as form data: %s", err.Error())
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}

			file, handler, err := r.FormFile("ca.crt")
			if err != nil {
				fmt.Printf("error parsing request body for certificate: %s", err.Error())
				http.Error(w, err.Error(), http.StatusBadRequest)
				return
			}
			defer file.Close()
			// FIXME(alecmerdler): Debugging
			fmt.Printf("Uploaded File: %+v\n", handler.Filename)
			fmt.Printf("File Size: %+v\n", handler.Size)
			fmt.Printf("MIME Header: %+v\n", handler.Header)

			fileBytes, err := ioutil.ReadAll(file)
			if err != nil {
				fmt.Printf("error reading certificate file: %s", err.Error())
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}

			certStore[handler.Filename] = fileBytes

			w.WriteHeader(201)
			w.Write([]byte("Success"))
		case "GET":
			certMeta := []map[string]interface{}{}
			for name, cert := range shared.LoadCerts(configDir) {
				certStore[name] = cert
			}

			for name := range certStore {
				md := map[string]interface{}{
					"path":    name,
					"names":   name,
					"expired": false,
				}
				certMeta = append(certMeta, md)
			}
			resp := map[string]interface{}{
				"status": "directory",
				"certs":  certMeta,
			}
			var json = jsoniter.ConfigCompatibleWithStandardLibrary
			js, err := json.Marshal(resp)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			w.Header().Add("Content-Type", "application/json")
			w.Write(js)
		default:
			w.WriteHeader(405)
			return
		}
	}
}

// certStore keeps all the uploaded certs in memory until they are committed.
var certStore = map[string][]byte{}

// RunConfigEditor runs the configuration editor server.
func RunConfigEditor(password string, configPath string, operatorEndpoint string) {
	mime.AddExtensionType(".css", "text/css; charset=utf-8")
	mime.AddExtensionType(".js", "application/javascript; charset=utf-8")

	log.Printf("Running the configuration editor on port %v with username %s", port, editorUsername)
	log.Printf("Using Operator Endpoint: " + operatorEndpoint)

	hashed, _ := bcrypt.GenerateFromPassword([]byte(password), 5)
	authenticator := auth.NewBasicAuthenticator(editorUsername, func(user, realm string) string {
		if user == editorUsername {
			return string(hashed)
		}
		return ""
	})

	http.HandleFunc("/", auth.JustCheck(authenticator, handler(operatorEndpoint)))
	http.HandleFunc("/api/v1/config", auth.JustCheck(authenticator, configHandler(configPath)))
	http.HandleFunc("/api/v1/certificates", auth.JustCheck(authenticator, certificateHandler(configPath)))
	http.HandleFunc("/api/v1/config/downloadConfig", auth.JustCheck(authenticator, downloadConfig(configPath)))
	http.HandleFunc("/api/v1/config/validate", auth.JustCheck(authenticator, configValidator(configPath)))
	http.HandleFunc("/api/v1/config/commitToOperator", auth.JustCheck(authenticator, commitToOperator(configPath, operatorEndpoint)))
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(staticContentPath))))

	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%v", port), nil))
}
