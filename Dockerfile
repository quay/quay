FROM golang:1.14

WORKDIR /go/src/config-tool

COPY . .

RUN go get -d -v ./...

RUN go install -v ./...

