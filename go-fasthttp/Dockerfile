FROM golang:1 AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY main.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /server .

FROM gcr.io/distroless/static-debian12
COPY --from=build /server /server
EXPOSE 8080
CMD ["/server"]
