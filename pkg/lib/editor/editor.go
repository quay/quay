// @title Config Tool Editor API
// @version 0.0
// @contact.name Jonathan King
// @contact.email joking@redhat.com
// @BasePath /api/v1
// @securityDefinitions.basic BasicAuth
// @schemes http

package editor

import (
	"log"
	"mime"
	"net/http"
	"os"
	"strconv"

	auth "github.com/abbot/go-http-auth"
	"github.com/go-chi/chi"
	"github.com/go-chi/chi/middleware"
	_ "github.com/quay/config-tool/docs"
	httpSwagger "github.com/swaggo/http-swagger"
	"golang.org/x/crypto/bcrypt"
)

// ServerOptions holds information regarding the set up of the config-tool server
type ServerOptions struct {
	username            string
	password            string
	port                int
	configPath          string
	staticContentPath   string
	operatorEndpoint    string
	readOnlyFieldGroups []string
	podNamespace        string // Optional
	podName             string // Optional
}

// ConfigBundle is the current state of the config bundle on the server. It may read from a path on disk and then edited through the API.
type ConfigBundle struct {
	Config             map[string]interface{} `json:"config.yaml" yaml:"config.yaml"`
	Certificates       map[string][]byte      `json:"certs,omitempty" yaml:"certs,omitempty"`
	ManagedFieldGroups []string               `json:"managedFieldGroups,omitempty" yaml:"managedFieldGroups,omitempty"`
}

// RunConfigEditor runs the configuration editor server.
func RunConfigEditor(password, configPath, operatorEndpoint string, readOnlyFieldGroups []string) {

	staticContentPath, exists := os.LookupEnv("CONFIG_EDITOR_STATIC_CONTENT_PATH")
	if !exists {
		staticContentPath = "pkg/lib/editor/static"
	}
	podNamespace := os.Getenv("MY_POD_NAMESPACE")
	podName := os.Getenv("MY_POD_NAME")
	if operatorEndpoint != "" && (podNamespace == "" || podName == "") {
		panic("If you would like to use operator reconfiguration features you must specify your namespace and pod name") // FIXME (jonathan) - come up with better error message
	}
	if readOnlyFieldGroups == nil {
		readOnlyFieldGroups = []string{}
	}

	opts := &ServerOptions{
		username:            "quayconfig", // FIXME (jonathan) - add option to change username
		password:            password,
		port:                8080, // FIXME (jonathan) - add option to change port
		configPath:          configPath,
		staticContentPath:   staticContentPath,
		operatorEndpoint:    operatorEndpoint,
		readOnlyFieldGroups: readOnlyFieldGroups,
		podNamespace:        podNamespace,
		podName:             podName,
	}

	hashed, _ := bcrypt.GenerateFromPassword([]byte(opts.password), 5)
	authenticator := auth.NewBasicAuthenticator(opts.username, func(user, realm string) string {
		if user == opts.username {
			return string(hashed)
		}
		return ""
	})

	mime.AddExtensionType(".css", "text/css; charset=utf-8")
	mime.AddExtensionType(".js", "application/javascript; charset=utf-8")

	log.Printf("Running the configuration editor on port %v with username %s", opts.port, opts.username)
	if opts.operatorEndpoint != "" {
		log.Printf("Using Operator Endpoint: " + opts.operatorEndpoint)
	}

	r := chi.NewRouter()
	r.Use(middleware.Logger)

	// Function handlers
	r.Get("/", rootHandler(opts))
	r.Get("/api/v1/config", auth.JustCheck(authenticator, getMountedConfigBundle(opts)))
	r.Post("/api/v1/config/validate", auth.JustCheck(authenticator, validateConfigBundle(opts)))
	r.Post("/api/v1/config/download", auth.JustCheck(authenticator, downloadConfigBundle(opts)))
	r.Post("/api/v1/config/operator", auth.JustCheck(authenticator, commitToOperator(opts)))

	r.Get("/swagger/*", httpSwagger.Handler(
		httpSwagger.URL("http://localhost:7070/docs/swagger.json"), // FIXME(jonathan) - This can eventually be changed to the github link to this file.
	))

	// File handlers
	r.Get("/static/*", func(w http.ResponseWriter, r *http.Request) {
		fs := http.StripPrefix("/static/", http.FileServer(http.Dir(opts.staticContentPath)))
		fs.ServeHTTP(w, r)
	})
	r.Get("/docs/*", func(w http.ResponseWriter, r *http.Request) {
		fs := http.StripPrefix("/docs/", http.FileServer(http.Dir("docs")))
		fs.ServeHTTP(w, r)
	})

	s := &http.Server{
		Addr:    ":" + strconv.Itoa(opts.port),
		Handler: r,
	}

	log.Fatal(s.ListenAndServe())

}
