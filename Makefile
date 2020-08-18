all: 

generate: 
	go run ./utils/generate/gen.go

install:

	go install ./...

test:
	go test ./pkg/lib/fieldgroups/...

clean: 
	rm ./pkg/lib/fieldgroups/*

run-local-prod:
	sudo podman build -t config-app:latest -f Dockerfile . && sudo podman run -p 7070:8080 -ti config-app:latest editor --configPath=/path/to/mounted/config.yaml --password=password

run-local-dev:
	sudo podman build -t config-app:dev -f Dockerfile.dev . && sudo podman run -p 7070:8080 -ti config-app:dev editor --configPath=/path/to/mounted/config.yaml --password=password