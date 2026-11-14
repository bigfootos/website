FROM docker.io/library/alpine:latest AS assets

RUN apk add --no-cache libwebp-tools rsvg-convert
WORKDIR /src
COPY ./scripts/build-assets.sh ./scripts/build-assets.sh
COPY ./site ./site
RUN sh ./scripts/build-assets.sh

FROM nginx

COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=assets /src/site /usr/share/nginx/html

EXPOSE 80
