
#!/usr/bin/env bash
# Требуется установленный newman: npm i -g newman
mkdir -p reports
newman run postman/API_Car_Dealer.postman_collection.json -e postman/API_Car_Dealer.postman_environment.json --reporters cli,htmlextra --reporter-htmlextra-export reports/postman.html
