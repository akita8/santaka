FROM golang:1.15 as builder

WORKDIR /build

COPY . .

RUN CGO_ENABLED=0 go build

RUN go test -race ./...

FROM alpine:latest  

COPY --from=builder /build/backend .

ENTRYPOINT [ "/backend" ]