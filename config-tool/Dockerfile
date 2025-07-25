FROM registry.access.redhat.com/ubi8/ubi:latest as jsbuild

WORKDIR /jssrc
COPY pkg/lib/editor .
RUN yum install -y nodejs && \
    npm install --ignore-engines && \
    npm run build

FROM golang:1.24-alpine

RUN apk update && apk add ca-certificates && rm -rf /var/cache/apk/* && mkdir /usr/local/share/ca-certificates/extra
WORKDIR /go/src/config-tool
COPY . .
RUN rm -rf /go/src/config-tool/pkg/lib/editor/static/build
COPY --from=jsbuild /jssrc/static/build /go/src/config-tool/pkg/lib/editor/static/build

RUN go get -d -v ./...
RUN go install -v ./...

ENTRYPOINT [ "config-tool" ]
