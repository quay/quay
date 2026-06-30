FROM registry.access.redhat.com/ubi9/nodejs-22:latest@sha256:a83e4ae4bef9954136fdd4718448620b1f49338031c8a0ee4d8adb2a1bf3c1af AS build

ARG quay_app_api_url=http://localhost:8080
ENV REACT_QUAY_APP_API_URL=${quay_app_api_url}

RUN npm install -g pnpm@10
WORKDIR /opt/app-root
COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm run build

FROM registry.access.redhat.com/ubi9/nodejs-22-minimal:latest@sha256:fe289fffb6afcb931bbc3012bd793dd54d5775fd8c19202219a0a13654a4cdc9

WORKDIR /opt/app-root
COPY --from=build /opt/app-root/dist /opt/app-root/dist
COPY --from=build /opt/app-root/server.js /opt/app-root/server.js
EXPOSE 9000

CMD ["node", "server.js"]
