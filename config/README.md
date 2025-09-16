# Configuration Guide
**Stellar Hummingbot Connector v3.0**

**Last Updated:** 2025-09-16 06:46 UTC

## 📁 Configuration Overview

This directory contains all configuration files for the Stellar Hummingbot Connector. For detailed setup instructions, see [CONFIGURATION.md](../CONFIGURATION.md).

### 🗂️ Configuration Files

| File | Purpose | Environment |
|------|---------|-------------|
| `development.yml` | Local development settings | Development |
| `production.yml` | Production trading configuration | Production |
| `security.yml` | Security provider templates | All |
| `networks.yml` | Stellar network configurations | All |
| `integration_testing.yml` | Integration test settings | Testing |

### ⚡ Quick Start

#### **Development Setup**
```bash
# Copy and customize development config
cp config/development.yml config/local.yml
# Edit local.yml with your settings
# Start with development configuration
hummingbot start --config config/local.yml
```

#### **Production Setup**
```bash
# IMPORTANT: Never use production.yml directly
cp config/production.yml config/production-local.yml
# Customize with your production settings
# Deploy with production configuration
hummingbot start --config config/production-local.yml
```

### 🔧 Configuration Categories

#### **1. Network Configuration**
- Horizon API endpoints
- Soroban RPC endpoints
- Network passphrases
- Connection timeouts

#### **2. Security Configuration**
- Key management providers
- Authentication settings
- Encryption parameters
- Access controls

#### **3. Trading Configuration**
- Exchange settings
- Trading pair configurations
- Order management parameters
- Risk controls

#### **4. Operational Configuration**
- Logging levels and formats
- Monitoring and metrics
- Performance optimizations
- Error handling

### 🔒 Security Notes

1. **Never commit sensitive data**: Use environment variables for secrets
2. **Use templates**: Customize template files, don't modify originals
3. **Environment separation**: Separate configs for dev/staging/production
4. **Access controls**: Restrict access to production configurations

### 🔗 Related Documentation

- **Complete Setup**: [CONFIGURATION.md](../CONFIGURATION.md)
- **Security Setup**: [docs/PRODUCTION_SECURITY_GUIDE.md](../docs/PRODUCTION_SECURITY_GUIDE.md)
- **Network Details**: [README_networks.md](./README_networks.md)

---
*For comprehensive configuration instructions, always refer to the main [CONFIGURATION.md](../CONFIGURATION.md) file.*