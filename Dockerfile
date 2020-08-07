FROM centos:latest as jsbuild

WORKDIR /jssrc
COPY pkg/lib/editor .
RUN curl --silent --location https://rpm.nodesource.com/setup_12.x | bash - && \
    yum install -y nodejs && \
    curl --silent --location https://dl.yarnpkg.com/rpm/yarn.repo | tee /etc/yum.repos.d/yarn.repo && \
    rpm --import https://dl.yarnpkg.com/rpm/pubkey.gpg && \
    yum install -y yarn && \
    yarn install --ignore-engines && \
    yarn build

FROM golang:1.14

WORKDIR /go/src/config-tool
COPY . .
RUN rm -rf /go/src/config-tool/pkg/lib/editor/static/build
COPY --from=jsbuild /jssrc/static/build /go/src/config-tool/pkg/lib/editor/static/build

RUN go get -d -v ./...
RUN go install -v ./... 

ENTRYPOINT [ "config-tool" ]
