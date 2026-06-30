FROM golang:1.25.11-alpine3.24@sha256:523c3effe300580ed375e43f43b1c9b091b68e935a7c3a92bfcc4e7ed55b18c2

RUN apk update && apk add ca-certificates && rm -rf /var/cache/apk/* && mkdir /usr/local/share/ca-certificates/extra
WORKDIR /go/src/config-tool
COPY . .

RUN go get -d -v ./...
RUN go install -v ./...

ENTRYPOINT [ "config-tool" ]
