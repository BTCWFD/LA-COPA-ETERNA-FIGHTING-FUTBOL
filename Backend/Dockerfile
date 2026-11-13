# ============================================================================
# Dockerfile — Microservicio de Arbitraje eSports y Replays ("La Copa Eterna")
# Compilación Multi-Stage estática en Go 1.22 sobre Alpine Linux
# ============================================================================

FROM golang:1.22-alpine AS builder

WORKDIR /src
COPY go.mod ./
COPY cmd/ ./cmd/

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath -ldflags="-s -w" -o /out/saf-arbitration-server ./cmd/arbitration-server

FROM alpine:3.20

RUN apk --no-cache add ca-certificates tzdata && \
    addgroup -S safgroup && adduser -S safuser -G safgroup

WORKDIR /app
COPY --from=builder /out/saf-arbitration-server /app/saf-arbitration-server

USER safuser
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1

ENTRYPOINT ["/app/saf-arbitration-server"]
