package editor

import (
	"archive/tar"
	"bytes"
	"fmt"
	"io/ioutil"
	"net/http"
	"path"
	"strings"

	jsoniter "github.com/json-iterator/go"
	"github.com/quay/config-tool/pkg/lib/config"
	"github.com/quay/config-tool/pkg/lib/shared"
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

// @Summary Returns the mounted config bundle.
// @Description This endpoint will load the config bundle mounted by the config-tool into memory. This state can then be modified, validated, downloaded, and optionally committed to a Quay operator instance.
// @Produce  json
// @Header 200 {string} Token "qwerty"
// @Router /config [get]
func getMountedConfigBundle(opts *ServerOptions) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {

		// Read config file
		configFilePath := path.Join(opts.configPath, "config.yaml")
		configBytes, err := ioutil.ReadFile(configFilePath)
		if err != nil {
			http.Error(w, err.Error(), http.StatusNotFound)
			return
		}

		// Load config into struct
		var config map[string]interface{}
		if err = yaml.Unmarshal(configBytes, &config); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Get all certs in directory
		certs := shared.LoadCerts(opts.configPath)

		fmt.Println(len(certs))
		resp := ConfigBundle{
			Config:       config,
			Certificates: certs,
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

// @Summary Downloads a config bundle as a tar.gz
// @Description This endpoint will download the config bundle in the request body as a tar.gz
// @Accept  json
// @Produce  json
// @Success 200
// @Header 200
// @Failure 400
// @Failure 404
// @Failure 500
// @Router /config/downloadConfig [post]
func downloadConfigBundle(opts *ServerOptions) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		var confBundle ConfigBundle
		err := yaml.NewDecoder(r.Body).Decode(&confBundle)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		files := make(map[string][]byte)
		files["config.yaml"], err = yaml.Marshal(confBundle.Config)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		for certName, contents := range confBundle.Certificates {
			files[certName] = contents
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

// @Summary Validates a config bundle.
// @Description N/A
// @Accept  json
// @Produce  json
// @Success 200 {object} model.Account
// @Header 200 {string} Token "qwerty"
// @Failure 400 {object} httputil.HTTPError
// @Failure 404 {object} httputil.HTTPError
// @Failure 500 {object} httputil.HTTPError
// @Router /accounts/{id} [get]
func validateConfigBundle(opts *ServerOptions) func(http.ResponseWriter, *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {

		if r.Method != "POST" {
			w.WriteHeader(405)
			return
		}

		var configBundle ConfigBundle
		err := yaml.NewDecoder(r.Body).Decode(&configBundle)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		loaded, err := config.NewConfig(configBundle.Config)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		opts := shared.Options{
			Mode:         "online",
			Certificates: configBundle.Certificates,
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

// @Summary Commits a config bundle to a Quay operator instance.
// @Description N/A
// @Accept  json
// @Produce  json
// @Success 200 {object} model.Account
// @Header 200 {string} Token "qwerty"
// @Failure 400 {object} httputil.HTTPError
// @Failure 404 {object} httputil.HTTPError
// @Failure 500 {object} httputil.HTTPError
// @Router /accounts/{id} [get]
// commitToOperator handles an HTTP POST request containing a new `config.yaml`,
// adds any uploaded certs, and calls an API endpoint on the Quay Operator to create a new `Secret`.
func commitToOperator(opts *ServerOptions) func(w http.ResponseWriter, r *http.Request) {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			w.WriteHeader(405)
			return
		}

		var configBundle ConfigBundle
		err := yaml.NewDecoder(r.Body).Decode(&configBundle)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// TODO(alecmerdler): For each managed component fieldgroup, remove its fields from `config.yaml` using `Fields()` function...
		newConfig, err := config.NewConfig(configBundle.Config)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		for _, fieldGroup := range configBundle.ManagedFieldGroups {
			fields := newConfig[fieldGroup].Fields()
			// FIXME(alecmerdler): Debugging
			fmt.Println(fields)
			for _, field := range fields {
				delete(configBundle.Config, field)
			}
		}

		// TODO: Define struct type for this with correct `yaml` tags
		preSecret := map[string]interface{}{
			"quayRegistryName": strings.Split(opts.podName, "-quay-config-editor")[0],
			"namespace":        opts.podNamespace,
			"config.yaml":      configBundle.Config,
			"certs":            configBundle.Certificates,
		}

		var json = jsoniter.ConfigCompatibleWithStandardLibrary
		js, err := json.Marshal(preSecret)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}

		// FIXME: Currently hardcoding
		req, err := http.NewRequest("POST", opts.operatorEndpoint+"/reconfigure", bytes.NewBuffer(js))
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
