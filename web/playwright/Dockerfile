FROM src
RUN dnf module enable -y nodejs:20 && \
    dnf install -y nodejs \
    alsa-lib atk at-spi2-atk cups-libs libdrm libXcomposite \
    libXdamage libXrandr mesa-libgbm pango nss nss-util nspr \
    libxkbcommon libXfixes libXcursor libXext libXi libXtst \
    libwayland-client && \
    dnf clean all
WORKDIR /go/src/github.com/quay/quay/web
RUN npm ci
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN npx playwright install chromium
