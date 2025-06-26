Tạo docker:
 + docker run -d --name nghia-container -e MYSQL_ROOT_PASSWORD=nghia123456 -e MYSQL_DATABASE=nghia-db -p 3306:3306 --hostname nghia-db --rm mysql:latest 