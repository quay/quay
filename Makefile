include .env

PID_FILE=/tmp/go_id.pid

all: 

generate: 
	go run ./utils/generate/gen.go

install:

	go install ./...

test:
	go test ./pkg/lib/fieldgroups/...

# Used to bring up production container
run-local-prod:
	sudo podman build -t config-app:latest -f Dockerfile . && sudo podman run -p 7070:8080 -v ${CONFIG_MOUNT}:/conf -ti config-app:latest editor --config-dir=/conf --password=password --operator-endpoint=${OPERATOR_ENDPOINT}

# Used to bring up dev container
build-local-dev:
	sudo podman build -t config-app:dev -f Dockerfile.dev

run-local-dev:
	sudo podman run -p 7070:8080 \
	-v ./pkg/lib/editor/js:/jssrc/js \
	-v ./pkg/lib/editor/editor.go:/jssrc/editor.go \
	-v ./:/go/src/config-tool \
	-v ${CONFIG_MOUNT}:/conf \
	-v ./testdata-tls/localhost.key:${CONFIG_TOOL_PRIVATE_KEY} \
	-v ./testdata-tls/localhost.crt:${CONFIG_TOOL_PUBLIC_KEY} \
	-e MY_POD_NAMESPACE=${MY_POD_NAMESPACE} \
	-e MY_POD_NAME=${MY_POD_NAME} \
	-e CONFIG_TOOL_PUBLIC_KEY=${CONFIG_TOOL_PUBLIC_KEY} \
	-e CONFIG_TOOL_PRIVATE_KEY=${CONFIG_TOOL_PRIVATE_KEY} \
	-ti config-app:dev

swagger:
	swag init -g pkg/lib/editor/editor.go