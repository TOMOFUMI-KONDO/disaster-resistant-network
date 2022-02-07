.PHONY: build
build: bin/server bin/client

bin/server: server/main.go
	go build -o bin/server server/main.go

bin/client: client/main.go
	go build -o bin/client client/main.go
