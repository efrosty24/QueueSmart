# Build the React frontend
FROM node:26-alpine AS build
# Node images ship an older npm; upgrade to the version the project uses.
ARG NPM_VERSION=12.2.0
RUN npm install -g npm@${NPM_VERSION}
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Serve the static build with nginx
FROM nginx:alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
