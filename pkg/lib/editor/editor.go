package editor

import (
	"fmt"
	"log"
	"mime"
	"net/http"
	"os"

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

// ConfigState is the current state of the config bundle on the server. It may read from a path on disk and then edited through the API.
type ConfigState struct {
	Config       map[string]interface{}
	Certificates []byte
}

// @title Config Tool Editor API
// @version 0.0

// @contact.name Jonathan King
// @contact.email joking@redhat.com

// @host localhost:8080
// @BasePath /api/v1

// RunConfigEditor runs the configuration editor server.
func RunConfigEditor(password, configPath, operatorEndpoint string, readOnlyFieldGroups []string) {

	staticContentPath, exists := os.LookupEnv("CONFIG_EDITOR_STATIC_CONTENT_PATH")
	if !exists {
		staticContentPath = "pkg/lib/editor/static"
	}
	podNamespace := os.Getenv("MY_POD_NAMESPACE")
	podName := os.Getenv("MY+_POD_NAME")
	if operatorEndpoint != "" && (podNamespace == "" || podName == "") {
		panic("If you would like to use operator reconfiguration features you must specify your namespace and pod name") // FIXME (jonathan) - come up with better error message
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
	configState := &ConfigState{}

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

	r.Get("/", rootHandler(opts))
	r.Get("/api/v1/config", auth.JustCheck(authenticator, loadMountedConfigBundle(opts, configState)))
	// http.HandleFunc("/api/v1/config", auth.JustCheck(authenticator, loadMountedConfigBundle(opts, configState)))
	// http.HandleFunc("/api/v1/certificates", auth.JustCheck(authenticator, certificateHandler(configPath)))
	// http.HandleFunc("/api/v1/config/downloadConfig", auth.JustCheck(authenticator, downloadConfig(configPath)))
	// http.HandleFunc("/api/v1/config/validate", auth.JustCheck(authenticator, configValidator(configPath)))
	// http.HandleFunc("/api/v1/config/commitToOperator", auth.JustCheck(authenticator, commitToOperator(opts)))
	r.Get("/swagger/*", httpSwagger.Handler(
		httpSwagger.URL("http://localhost:7070/docs/swagger.json"), // FIXME(jonathan) - This can eventually be changed to the github link to this file.
	))

	r.Get("/static/*", func(w http.ResponseWriter, r *http.Request) {
		fs := http.StripPrefix("/static/", http.FileServer(http.Dir(opts.staticContentPath)))
		fs.ServeHTTP(w, r)
	})

	// Once swagger.json is on github, we don't need to serve it (this is just for testing)
	r.Get("/docs/*", func(w http.ResponseWriter, r *http.Request) {
		fs := http.StripPrefix("/docs/", http.FileServer(http.Dir("docs")))
		fs.ServeHTTP(w, r)
	})

	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%v", opts.port), r))
}
