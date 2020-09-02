package editor

import (
	"bytes"
	"fmt"
	"io/ioutil"
	"log"
	"mime"
	"net/http"
	"os"
	"path"
	"path/filepath"

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

func handler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/" {
		p := staticContentPath + "/index.html"
		http.ServeFile(w, r, p)
		return
	}

	w.WriteHeader(404)
}

// posts to operator to commit
func commitToOperator(configPath, operatorEndpoint string) func(w http.ResponseWriter, r *http.Request) {

	return func(w http.ResponseWriter, r *http.Request) {

		if r.Method != "POST" {
			w.WriteHeader(404)
			return
		}

		var conf map[string]interface{}
		err := yaml.NewDecoder(r.Body).Decode(&conf)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		certs := shared.LoadCerts(configPath)
		preSecret := map[string]interface{}{
			"config.yaml": conf,
			"certs":       certs,
		}

		var json = jsoniter.ConfigCompatibleWithStandardLibrary
		js, err := json.Marshal(preSecret)

		// currently hardcoding
		req, err := http.NewRequest("POST", operatorEndpoint, bytes.NewBuffer(js))
		req.Header.Set("Content-Type", "application/json")
		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			fmt.Println(err.Error())
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
		if r.Method != "GET" {
			w.WriteHeader(405)
			return
		}

		// Create output file
		out, err := os.Create("/tmp/quay-config.tar.gz")
		if err != nil {
			log.Fatalln("Error writing archive:", err)
		}
		defer out.Close()

		// Create the archive and write the output to the "out" Writer
		err = shared.CreateArchive(configPath, out)
		if err != nil {
			log.Fatalln("Error creating archive:", err)
		}

		w.Header().Set("Content-type", "application/zip")
		http.ServeFile(w, r, "/tmp/quay-config.tar.gz")
	}
}

// post request to validate config with certs
func configValidator(configPath string) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {

		if r.Method != "POST" {
			w.WriteHeader(404)
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

		certs := shared.LoadCerts(configPath)
		opts := shared.Options{
			Mode:         "online",
			Certificates: certs,
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
			w.WriteHeader(404)
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

func getCertificates(configPath string) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			w.WriteHeader(404)
			return
		}

		certMeta := []map[string]interface{}{}
		certs := shared.LoadCerts(configPath)

		for name := range certs {
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
	}
}

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

	http.HandleFunc("/", auth.JustCheck(authenticator, handler))
	http.HandleFunc("/api/v1/config", auth.JustCheck(authenticator, configHandler(configPath)))
	http.HandleFunc("/api/v1/certificates", auth.JustCheck(authenticator, getCertificates(configPath)))
	http.HandleFunc("/api/v1/config/downloadConfig", auth.JustCheck(authenticator, downloadConfig(configPath)))
	http.HandleFunc("/api/v1/config/validate", auth.JustCheck(authenticator, configValidator(configPath)))
	http.HandleFunc("/api/v1/config/commitToOperator", auth.JustCheck(authenticator, commitToOperator(configPath, operatorEndpoint)))
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(staticContentPath))))

	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%v", port), nil))
}
