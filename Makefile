APP := ipcrawler

.PHONY: build check clean

build:
	go build -o $(APP) .

check:
	go vet ./... && golangci-lint run ./...

clean:
	rm -f $(APP)
