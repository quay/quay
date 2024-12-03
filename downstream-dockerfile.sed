s|FROM registry.access.redhat.com/ubi8/ubi-minimal|FROM registry.redhat.io/rhel8-6-els/rhel|
s|microdnf|dnf|
s|dnf remove |dnf remove -y|

# /^FROM .* [Aa][Ss] config-editor$/,/^FROM /{
# 	s|^WORKDIR .*|WORKDIR .quay/config-tool/pkg/lib/editor|
# 	# s|^COPY --chown=1001:0 config-tool/.*|COPY --chown=1001:0 $REMOTE_SOURCES $REMOTE_SOURCES_DIR|
# }

# /^FROM .* [Aa][Ss] build-python$/,/^FROM /{
# # 	/^FROM .* [Aa][Ss] build-python$/a\
# # COPY cargo/config.toml /root/.cargo/config.toml\
# # COPY cargo/vendor/ /opt/cargo/vendor/
# 	# s|^WORKDIR .*|WORKDIR $REMOTE_SOURCES_DIR/quay/app|
# 	# s|^COPY requirements.txt \.$|COPY $REMOTE_SOURCES $REMOTE_SOURCES_DIR|
# 	s|microdnf|dnf|
# 	s|dnf remove|dnf remove -y|
# 	# s|python3 -m pip install|source $REMOTE_SOURCES_DIR/quay/cachito.env \&\& python3 -m pip install|
# }

# /^RUN ARCH=$(uname -m) ; echo $ARCH; .*/,/^RUN /{
# 	/^RUN set/!d
# }

# /^FROM .* [Aa][Ss] build-static$/,/^FROM /{
# 	# s|^WORKDIR .*|WORKDIR $REMOTE_SOURCES_DIR/quay/app|
# 	# s|^COPY --chown=1001:0 package\.json.*|COPY --chown=1001:0 $REMOTE_SOURCES $REMOTE_SOURCES_DIR|
# 	\|COPY --chown=1001:0 static/.*|d
# 	\|COPY --chown=1001:0 \*\.json.*|d
# }

# /^FROM .* [Aa][Ss] build-ui$/,/^FROM /{
# 	# s|^WORKDIR .*|WORKDIR $REMOTE_SOURCES_DIR/quay/app/web|
# 	# s|^COPY --chown=1001:0 web/package\.json.*|COPY --chown=1001:0 $REMOTE_SOURCES $REMOTE_SOURCES_DIR|
# 	\|COPY --chown=1001:0 web.*|d
# }

# /^FROM .* [Aa][Ss] pushgateway$/,/^FROM /{
# 	/^FROM .* [Aa][Ss] pushgateway$/{
# 		i\
# FROM registry.access.redhat.com/ubi8/go-toolset:1.19 AS pushgateway\
# RUN go mod vendor && GOEXPERIMENT=strictfipsruntime go build -tags strictfipsruntime\
# \
# # Config-tool builds the go binary in the configtool.
# 		d
# 	}
# 	/^FROM /!d
# }

# /^FROM .* [Aa][Ss] config-tool/,/^FROM /{
# 	# s|WORKDIR /opt/app-root/src|WORKDIR $REMOTE_SOURCES_DIR/quay/app/config-tool|
# 	# s|^COPY config-tool/.*|COPY $REMOTE_SOURCES $REMOTE_SOURCES_DIR|
# 	s|go install -tags=|GOEXPERIMENT=strictfipsruntime go install -tags strictfipsruntime,|
# 	# s|COPY --from=config-editor /opt/app-root/src/static/build  */opt/app-root/src/pkg/lib/editor/static/build|COPY --from=config-editor $REMOTE_SOURCES_DIR/quay/app/config-tool/pkg/lib/editor/static/build $REMOTE_SOURCES_DIR/quay/app/config-tool/pkg/lib/editor/static/build|
# }

# /^FROM .* [Aa][Ss] build-quaydir$/,/^FROM /{
# 	# s|COPY --from=config-editor /opt/app-root/src |COPY --from=config-editor $REMOTE_SOURCES_DIR/quay/app/config-tool/pkg/lib/editor |
# 	# s|COPY --from=build-static /opt/app-root/src/static |COPY --from=build-static $REMOTE_SOURCES_DIR/quay/app/static |
# 	# s|COPY --from=build-ui /opt/app-root/dist |COPY --from=build-ui $REMOTE_SOURCES_DIR/quay/app/web/dist |
# 	# s|COPY --chown=0:0 \. \.|COPY --chown=0:0 $REMOTE_SOURCES/quay/app .|
# 	\|	; curl -fsSL https://ip-ranges.amazonaws.com/ip-ranges.json -o util/ipresolver/aws-ip-ranges.json\\|d
# }

/^FROM .* [Aa][Ss] final$/,/^FROM /{
	/^LABEL maintainer "quay-devel@redhat.com"/{
		i\
LABEL com.redhat.component="quay-registry-container"\
LABEL name="quay/quay-rhel8"\
LABEL io.k8s.display-name="Red Hat Quay"\
LABEL io.k8s.description="Red Hat Quay"\
LABEL summary="Red Hat Quay"\
LABEL maintainer="support@redhat.com"\
LABEL io.openshift.tags="quay"\
ENV RED_HAT_QUAY=true
		d
	}
	# s|COPY --from=pushgateway /usr/local/bin/pushgateway |COPY --from=pushgateway $REMOTE_SOURCES_DIR/pushgateway/app/pushgateway |
	# s|COPY --from=config-tool /opt/app-root/src/go/bin/config-tool |COPY --from=config-tool $REMOTE_SOURCES_DIR/quay/deps/gomod/bin/config-tool |
	# s|microdnf|dnf|
	# s|dnf remove|dnf remove -y|
}

# /^FROM .* [Aa][Ss] /{
# 	h
# 	s/^FROM \(.*\) [Aa][Ss] .*/#@follow_tag(\1)/
# 	G
# }
