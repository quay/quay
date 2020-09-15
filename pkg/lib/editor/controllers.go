package editor

import (
	"io/ioutil"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strings"

	jsoniter "github.com/json-iterator/go"
	"gopkg.in/yaml.v2"
)

func rootHandler(opts *ServerOptions) func(w http.ResponseWriter, r *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" {
			p := opts.staticContentPath + "/index.html"

			if len(opts.operatorEndpoint) > 0 {
				http.SetCookie(w, &http.Cookie{Name: "QuayOperatorEndpoint", Value: opts.operatorEndpoint})
			}

			http.SetCookie(w, &http.Cookie{Name: "QuayReadOnlyFieldGroups", Value: strings.Join(opts.readOnlyFieldGroups, ",")})

			http.ServeFile(w, r, p)
			return
		}

		w.WriteHeader(404)
	}
}

// // downloadConfig
// func downloadConfigState(opts *ServerOptions, confState *ConfigState) func(http.ResponseWriter, *http.Request) {

// 	return func(w http.ResponseWriter, r *http.Request) {
// 		if r.Method != "POST" {
// 			w.WriteHeader(405)
// 			return
// 		}

// 		var conf map[string]interface{}
// 		err := yaml.NewDecoder(r.Body).Decode(&conf)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		for name, cert := range shared.LoadCerts(opts.configPath) {
// 			certStore[name] = cert
// 		}

// 		files := make(map[string][]byte)
// 		files["config.yaml"], err = yaml.Marshal(conf)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusInternalServerError)
// 			return
// 		}
// 		for name, contents := range certStore {
// 			files[name] = contents
// 		}

// 		var buf bytes.Buffer
// 		tw := tar.NewWriter(&buf)
// 		hdr := &tar.Header{
// 			Name:     "extra_ca_certs/",
// 			Typeflag: tar.TypeDir,
// 			Mode:     0777,
// 		}
// 		if err := tw.WriteHeader(hdr); err != nil {
// 			http.Error(w, err.Error(), http.StatusInternalServerError)
// 			return
// 		}
// 		for name, contents := range files {
// 			hdr := &tar.Header{
// 				Name: name,
// 				Mode: 0777,
// 				Size: int64(len(contents)),
// 			}
// 			if err := tw.WriteHeader(hdr); err != nil {
// 				http.Error(w, err.Error(), http.StatusInternalServerError)
// 				return
// 			}
// 			if _, err := tw.Write(contents); err != nil {
// 				http.Error(w, err.Error(), http.StatusInternalServerError)
// 				return
// 			}
// 		}
// 		tw.Close()

// 		w.Header().Set("Content-type", "application/zip")
// 		w.Header().Set("Content-Disposition", "attachment; filename=quay-config.tar.gz")
// 		w.Write(buf.Bytes())
// 	}

// }

// // @Summary Validate a configuration state
// // @Description This endpoint will validate a configuration state.
// // @Accept  json
// // @Produce  json
// // @Success 200 {object} model.Account
// // @Header 200 {string} Token "qwerty"
// // @Failure 400 {object} httputil.HTTPError
// // @Failure 404 {object} httputil.HTTPError
// // @Failure 500 {object} httputil.HTTPError
// // @Router /accounts/{id} [get]
// func validateConfigState(configPath string, certStore map[string][]byte) func(http.ResponseWriter, *http.Request) {
// 	return func(w http.ResponseWriter, r *http.Request) {

// 		if r.Method != "POST" {
// 			w.WriteHeader(405)
// 			return
// 		}

// 		var c map[string]interface{}
// 		err := yaml.NewDecoder(r.Body).Decode(&c)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		loaded, err := config.NewConfig(c)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		for name, cert := range shared.LoadCerts(configPath) {
// 			certStore[name] = cert
// 		}

// 		opts := shared.Options{
// 			Mode:         "online",
// 			Certificates: certStore,
// 		}

// 		errors := loaded.Validate(opts)

// 		var json = jsoniter.ConfigCompatibleWithStandardLibrary
// 		js, err := json.Marshal(errors)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusInternalServerError)
// 			return
// 		}

// 		w.Header().Add("Content-Type", "application/json")
// 		w.Write(js)
// 	}
// }

// @Summary Load the mounted config bundle into local state
// @Description This endpoint will validate a configuration state.
// @Accept  json
// @Produce  json
// @Header 200 {string} Token "qwerty"
// @Router /accounts/{id} [get]
func loadMountedConfigBundle(opts *ServerOptions, configState *ConfigState) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			w.WriteHeader(405)
			return
		}

		// Read config file
		configFilePath := path.Join(opts.configPath, "config.yaml")
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
		err = filepath.Walk(opts.configPath, func(path string, info os.FileInfo, err error) error {
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

// // @Summary Load the mounted config bundle into local state
// // @Description This endpoint will validate a configuration state.
// // @Accept  json
// // @Produce  json
// // @Success 200 {object} model.Account
// // @Header 200 {string} Token "qwerty"
// // @Failure 400 {object} httputil.HTTPError
// // @Failure 404 {object} httputil.HTTPError
// // @Failure 500 {object} httputil.HTTPError
// // @Router /accounts/{id} [get]
// func uploadCertificate(configDir string) func(http.ResponseWriter, *http.Request) {
// 	return func(w http.ResponseWriter, r *http.Request) {

// 		err := r.ParseMultipartForm(10 << 20)
// 		if err != nil {
// 			fmt.Printf("error parsing request body as form data: %s", err.Error())
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		file, handler, err := r.FormFile("ca.crt")
// 		if err != nil {
// 			fmt.Printf("error parsing request body for certificate: %s", err.Error())
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}
// 		defer file.Close()
// 		// FIXME(alecmerdler): Debugging
// 		fmt.Printf("Uploaded File: %+v\n", handler.Filename)
// 		fmt.Printf("File Size: %+v\n", handler.Size)
// 		fmt.Printf("MIME Header: %+v\n", handler.Header)

// 		fileBytes, err := ioutil.ReadAll(file)
// 		if err != nil {
// 			fmt.Printf("error reading certificate file: %s", err.Error())
// 			http.Error(w, err.Error(), http.StatusInternalServerError)
// 			return
// 		}

// 		certStore[handler.Filename] = fileBytes

// 		w.WriteHeader(201)
// 		w.Write([]byte("Success"))

// 	}
// }

// func getCertificates(configDir string) func(http.ResponseWriter, *http.Request) {
// 	return func(w http.ResponseWriter, r *http.Request) {

// 		certMeta := []map[string]interface{}{}
// 		for name, cert := range shared.LoadCerts(configDir) {
// 			certStore[name] = cert
// 		}

// 		for name := range certStore {
// 			md := map[string]interface{}{
// 				"path":    name,
// 				"names":   name,
// 				"expired": false,
// 			}
// 			certMeta = append(certMeta, md)
// 		}
// 		resp := map[string]interface{}{
// 			"status": "directory",
// 			"certs":  certMeta,
// 		}
// 		var json = jsoniter.ConfigCompatibleWithStandardLibrary
// 		js, err := json.Marshal(resp)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusInternalServerError)
// 			return
// 		}
// 		w.Header().Add("Content-Type", "application/json")
// 		w.Write(js)

// 	}
// }

// type commitRequest struct {
// 	Config             map[string]interface{} `json:"config.yaml" yaml:"config.yaml"`
// 	ManagedFieldGroups []string               `json:"managedFieldGroups" yaml:"managedFieldGroups"`
// }

// // commitToOperator handles an HTTP POST request containing a new `config.yaml`,
// // adds any uploaded certs, and calls an API endpoint on the Quay Operator to create a new `Secret`.
// func commitToOperator(opts *ServerOptions) func(w http.ResponseWriter, r *http.Request) {

// 	quayRegistryName := strings.Split(opts.podName, "-quay-config-editor")[0]

// 	return func(w http.ResponseWriter, r *http.Request) {
// 		if r.Method != "POST" {
// 			w.WriteHeader(405)
// 			return
// 		}

// 		var request commitRequest
// 		err := yaml.NewDecoder(r.Body).Decode(&request)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		for name, cert := range shared.LoadCerts(opts.configPath) {
// 			certStore[name] = cert
// 		}

// 		// TODO(alecmerdler): For each managed component fieldgroup, remove its fields from `config.yaml` using `Fields()` function...
// 		newConfig, err := config.NewConfig(request.Config)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		for _, fieldGroup := range request.ManagedFieldGroups {
// 			fields := newConfig[fieldGroup].Fields()
// 			// FIXME(alecmerdler): Debugging
// 			fmt.Println(fields)
// 			for _, field := range fields {
// 				delete(request.Config, field)
// 			}
// 		}

// 		// TODO: Define struct type for this with correct `yaml` tags
// 		preSecret := map[string]interface{}{
// 			"quayRegistryName": quayRegistryName,
// 			"namespace":        opts.podNamespace,
// 			"config.yaml":      request.Config,
// 			"certs":            certStore,
// 		}

// 		var json = jsoniter.ConfigCompatibleWithStandardLibrary
// 		js, err := json.Marshal(preSecret)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		// FIXME: Currently hardcoding
// 		req, err := http.NewRequest("POST", opts.operatorEndpoint+"/reconfigure", bytes.NewBuffer(js))
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusBadRequest)
// 			return
// 		}

// 		req.Header.Set("Content-Type", "application/json")
// 		client := &http.Client{}
// 		resp, err := client.Do(req)
// 		if err != nil {
// 			http.Error(w, err.Error(), http.StatusInternalServerError)
// 			return
// 		}

// 		defer resp.Body.Close()

// 		w.Header().Add("Content-Type", "application/json")
// 		w.Write(js)
// 	}
// }
