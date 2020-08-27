FROM centos:8 as jsbuild

WORKDIR /jssrc
COPY pkg/lib/editor .
RUN yum install -y nodejs && \
    npm install --ignore-engines && \
    npm run build

FROM golang:1.15

WORKDIR /go/src/config-tool
COPY . .
RUN rm -rf /go/src/config-tool/pkg/lib/editor/static/build
COPY --from=jsbuild /jssrc/static/build /go/src/config-tool/pkg/lib/editor/static/build

RUN go get -d -v ./...
RUN go install -v ./... 

ENTRYPOINT [ "config-tool" ]
