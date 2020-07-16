all: 

generate: 
	go run ./utils/generate/gen.go

install:

	go install ./...

test:
	go test ./pkg/lib/fieldgroups/...

clean: 
	rm ./pkg/lib/fieldgroups/*

