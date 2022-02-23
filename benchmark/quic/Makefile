GO=$(wildcard ../*.go)

build: bin/server bin/client

bin/server: server/main.go $(GO)
	go build -o bin/server server/main.go

bin/client: client/main.go $(GO)
	go build -o bin/client client/main.go

clean:
	rm -f bin/*
