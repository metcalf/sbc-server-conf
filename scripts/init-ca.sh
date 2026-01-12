#!/bin/bash
set -e

# Initialize a private Certificate Authority for itsshedtime.com
# This script creates a CA that can issue client certificates for device authentication

CA_DIR="$(cd "$(dirname "$0")/.." && pwd)/pki/ca"
CLIENTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/pki/clients"

echo "Initializing itsshedtime.com Certificate Authority..."
echo "CA Directory: $CA_DIR"

# Check if CA already exists
if [ -f "$CA_DIR/ca.key" ]; then
    echo "ERROR: CA already exists at $CA_DIR"
    echo "If you want to recreate the CA, manually delete the pki/ca directory first."
    exit 1
fi

# Create CA directory structure
mkdir -p "$CA_DIR"
mkdir -p "$CLIENTS_DIR"

# Generate CA private key (4096-bit RSA, encrypted with AES256)
echo ""
echo "Generating CA private key (you'll be asked for a passphrase)..."
openssl genrsa -aes256 -out "$CA_DIR/ca.key" 4096

# Generate CA certificate (valid for 10 years)
echo ""
echo "Generating CA certificate..."
openssl req -new -x509 -days 3650 -key "$CA_DIR/ca.key" \
    -out "$CA_DIR/ca.crt" \
    -subj "/C=US/ST=State/L=City/O=itsshedtime.com/OU=Home Infrastructure/CN=itsshedtime.com Root CA"

# Create serial number file
echo "1000" > "$CA_DIR/serial"

# Create index file for tracking issued certificates
touch "$CA_DIR/index.txt"

# Set secure permissions
chmod 600 "$CA_DIR/ca.key"
chmod 644 "$CA_DIR/ca.crt"

echo ""
echo "Certificate Authority created successfully!"
echo ""
echo "CA Certificate: $CA_DIR/ca.crt"
echo "CA Private Key: $CA_DIR/ca.key (KEEP THIS SECURE)"
echo ""
echo "Next steps:"
echo "1. Run ./scripts/issue-client-cert.sh <device-name> to create client certificates"
echo "2. Deploy the CA certificate to your server using Ansible"
echo "3. Install client certificates on your devices"
echo ""
echo "IMPORTANT: Back up the pki/ directory securely!"
