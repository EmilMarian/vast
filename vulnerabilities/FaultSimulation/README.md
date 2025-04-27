# Run a comprehensive demonstration of all fault types in sequence
./simulate-faults.sh --all

# Or simulate specific fault types
./simulate-faults.sh --sensor temperature-sensor-01 --fault stuck --duration 30
./simulate-faults.sh --sensor temperature-sensor-02 --fault drift --duration 60
./simulate-faults.sh --sensor temperature-sensor-03 --fault spike --duration 45
./simulate-faults.sh --sensor temperature-sensor-04 --fault dropout --duration 20



./simulate-faults.sh --sensor temperature-sensor-04 --fault spike --duration 60


./simulate-faults.sh  --sensor 192.168.1.109 --port 12381 --fault drift --duration 60
./simulate-faults.sh  --sensor 192.168.1.109 --port 12382 --fault spike --duration 60
./simulate-faults.sh  --sensor 192.168.1.109 --port 12383 --fault dropout --duration 60
./simulate-faults.sh  --sensor 192.168.1.109 --port 12384 --fault stuck --duration 60
