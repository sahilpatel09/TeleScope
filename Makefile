up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose up --build

down-with-volumes:
	docker-compose down --volumes