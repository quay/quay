FROM registry.access.redhat.com/ubi8/nodejs-16:latest as build

ARG quay_app_api_url=http://localhost:8080
ENV REACT_QUAY_APP_API_URL=${quay_app_api_url}

WORKDIR /opt/app-root
COPY package.json .
RUN npm install

COPY . .
RUN npm run build

FROM registry.access.redhat.com/ubi8/nodejs-16:latest

WORKDIR /opt/app-root
RUN npm install node-static
COPY --from=build  /opt/app-root/dist /opt/app-root/dist
COPY --from=build  /opt/app-root/server.js /opt/app-root/server.js
EXPOSE 9000

CMD ["node", "server.js"]

