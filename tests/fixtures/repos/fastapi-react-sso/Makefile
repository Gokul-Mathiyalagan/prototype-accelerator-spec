.PHONY: build test run

build:
	docker build -t team-insights .

test: build   # both test suites run during the image build

run:
	docker compose up --build
