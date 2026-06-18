# Security Policy

## Supported Versions

Currently, only the latest release of SYNAPSE_CORE (`v1.0.x`) is supported with security updates.

## Reporting a Vulnerability

SYNAPSE controls critical physical infrastructure (traffic lights via CARINA). As such, security is paramount. The system is designed around a **Zero-Trust** architecture, but vulnerabilities can still occur in neural inference layers or gRPC serialization.

> [!WARNING]
> **DO NOT** report security vulnerabilities via public GitHub Issues. 

If you discover a vulnerability, especially one related to:
- Sensor Data Injection Attacks
- Protobuf/gRPC Buffer Overflows
- Model Poisoning / Adversarial ML Attacks

Please email the details immediately to:
**security@noxfort.com**

We will acknowledge your email within 48 hours and provide a timeline for a patch. We ask that you do not publicly disclose the vulnerability until an official patch has been merged and distributed.
