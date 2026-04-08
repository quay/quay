FROM golang:1.24.8-alpine3.22

RUN apk update && apk add ca-certificates && rm -rf /var/cache/apk/* && mkdir /usr/local/share/ca-certificates/extra
WORKDIR /go/src/config-tool
COPY . .

RUN go get -d -v ./...
RUN go install -v ./...

ENTRYPOINT [ "config-tool" ]
