#!/bin/bash
set -e

# Issue a client certificate for device authentication
# Usage: ./issue-client-cert.sh <device-name>

if [ $# -ne 1 ]; then
    echo "Usage: $0 <device-name>"
    echo "Example: $0 andrews-laptop"
    exit 1
fi

DEVICE_NAME="$1"
CA_DIR="$(cd "$(dirname "$0")/.." && pwd)/pki/ca"
CLIENTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/pki/clients"
CLIENT_DIR="$CLIENTS_DIR/$DEVICE_NAME"

# Validate device name (alphanumeric and hyphens only)
if ! [[ "$DEVICE_NAME" =~ ^[a-zA-Z0-9-]+$ ]]; then
    echo "ERROR: Device name must contain only alphanumeric characters and hyphens"
    exit 1
fi

# Check if CA exists
if [ ! -f "$CA_DIR/ca.key" ] || [ ! -f "$CA_DIR/ca.crt" ]; then
    echo "ERROR: Certificate Authority not found. Run ./scripts/init-ca.sh first."
    exit 1
fi

# Check if client cert already exists
if [ -d "$CLIENT_DIR" ]; then
    echo "ERROR: Certificate for '$DEVICE_NAME' already exists at $CLIENT_DIR"
    echo "If you want to reissue, manually delete that directory first."
    exit 1
fi

echo "Issuing client certificate for: $DEVICE_NAME"
echo ""

# Create client directory
mkdir -p "$CLIENT_DIR"

# Generate client private key (2048-bit RSA, no passphrase for easier device use)
echo "Generating private key..."
openssl genrsa -out "$CLIENT_DIR/${DEVICE_NAME}.key" 2048

# Generate Certificate Signing Request (CSR)
echo "Generating certificate signing request..."
openssl req -new -key "$CLIENT_DIR/${DEVICE_NAME}.key" \
    -out "$CLIENT_DIR/${DEVICE_NAME}.csr" \
    -subj "/C=US/ST=State/L=City/O=itsshedtime.com/OU=Devices/CN=$DEVICE_NAME"

# Create OpenSSL config for the certificate
cat > "$CLIENT_DIR/cert.conf" <<EOF
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
EOF

# Sign the certificate with the CA (valid for 2 years)
echo "Signing certificate with CA (you'll need the CA passphrase)..."
openssl x509 -req -in "$CLIENT_DIR/${DEVICE_NAME}.csr" \
    -CA "$CA_DIR/ca.crt" \
    -CAkey "$CA_DIR/ca.key" \
    -CAserial "$CA_DIR/serial" \
    -out "$CLIENT_DIR/${DEVICE_NAME}.crt" \
    -days 730 \
    -extfile "$CLIENT_DIR/cert.conf"

# Create a PKCS#12 bundle for easy import (contains private key + certificate + CA cert)
echo ""
echo "Creating PKCS#12 bundle for device installation..."
echo "(You'll need to set an export password - can be empty for convenience)"
openssl pkcs12 -export \
    -out "$CLIENT_DIR/${DEVICE_NAME}.p12" \
    -inkey "$CLIENT_DIR/${DEVICE_NAME}.key" \
    -in "$CLIENT_DIR/${DEVICE_NAME}.crt" \
    -certfile "$CA_DIR/ca.crt" \
    -name "$DEVICE_NAME"

# Set secure permissions
chmod 600 "$CLIENT_DIR/${DEVICE_NAME}.key"
chmod 644 "$CLIENT_DIR/${DEVICE_NAME}.crt"
chmod 644 "$CLIENT_DIR/${DEVICE_NAME}.p12"

echo ""
echo "Client certificate issued successfully!"
echo ""
echo "Files created in: $CLIENT_DIR/"
echo "  ${DEVICE_NAME}.key - Private key"
echo "  ${DEVICE_NAME}.crt - Certificate"
echo "  ${DEVICE_NAME}.csr - Certificate signing request (can be deleted)"
echo "  ${DEVICE_NAME}.p12 - PKCS#12 bundle (easiest for device installation)"
echo ""
echo "Installation instructions:"
echo "1. Transfer ${DEVICE_NAME}.p12 to your device securely"
echo "2. Install the certificate:"
echo "   - iOS/macOS: Open the .p12 file and follow prompts"
echo "   - Android: Settings > Security > Install from storage"
echo "   - Linux/Firefox: Import in browser certificate manager"
echo "   - Windows: Double-click .p12 and import to 'Personal' store"
echo "3. Visit https://homeassistant.itsshedtime.com"
echo ""
echo "Certificate details:"
openssl x509 -in "$CLIENT_DIR/${DEVICE_NAME}.crt" -noout -subject -dates
