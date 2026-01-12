#!/bin/bash
set -e

# Generate a client certificate for Cloudflare mTLS
# Usage: ./generate-cloudflare-client-cert.sh <device-name>

if [ $# -ne 1 ]; then
    echo "Usage: $0 <device-name>"
    echo "Example: $0 andrews-laptop"
    exit 1
fi

DEVICE_NAME="$1"
CLIENTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/pki/cloudflare-clients"
CLIENT_DIR="$CLIENTS_DIR/$DEVICE_NAME"

# Validate device name (alphanumeric and hyphens only)
if ! [[ "$DEVICE_NAME" =~ ^[a-zA-Z0-9-]+$ ]]; then
    echo "ERROR: Device name must contain only alphanumeric characters and hyphens"
    exit 1
fi

# Check if client directory already exists
if [ -d "$CLIENT_DIR" ]; then
    echo "ERROR: Certificate for '$DEVICE_NAME' already exists at $CLIENT_DIR"
    echo "If you want to regenerate, manually delete that directory first."
    exit 1
fi

echo "Generating client certificate for: $DEVICE_NAME"
echo ""

# Create client directory
mkdir -p "$CLIENT_DIR"

# Generate client private key (2048-bit RSA)
echo "Step 1: Generating private key..."
openssl genrsa -out "$CLIENT_DIR/${DEVICE_NAME}.key" 2048

# Generate Certificate Signing Request (CSR)
echo "Step 2: Generating certificate signing request..."
openssl req -new -key "$CLIENT_DIR/${DEVICE_NAME}.key" \
    -out "$CLIENT_DIR/${DEVICE_NAME}.csr" \
    -subj "/C=US/ST=State/L=City/O=itsshedtime.com/OU=Devices/CN=$DEVICE_NAME"

# Set secure permissions
chmod 600 "$CLIENT_DIR/${DEVICE_NAME}.key"
chmod 644 "$CLIENT_DIR/${DEVICE_NAME}.csr"

echo ""
echo "✓ CSR generated successfully!"
echo ""
echo "=========================================="
echo "Step 3: Submit this CSR to Cloudflare:"
echo "=========================================="
echo ""
cat "$CLIENT_DIR/${DEVICE_NAME}.csr"
echo ""
echo "=========================================="
echo ""
echo "Instructions:"
echo "1. Go to: Cloudflare Dashboard > SSL/TLS > Edge Certificates > Client Certificates"
echo "2. Click 'Create Certificate'"
echo "3. Select 'Use my CSR'"
echo "4. Paste the CSR above"
echo "5. Set validity period (e.g., 10 years)"
echo "6. Click 'Create'"
echo "7. Copy the signed certificate from Cloudflare"
echo ""
read -p "Press Enter when you have the signed certificate ready to paste..."
echo ""
echo "Paste the certificate below (including -----BEGIN CERTIFICATE----- and -----END CERTIFICATE-----)"
echo "Press Ctrl+D when finished:"
echo ""

# Read certificate from stdin
certificate=$(cat)

# Save certificate
echo "$certificate" > "$CLIENT_DIR/${DEVICE_NAME}.crt"
chmod 644 "$CLIENT_DIR/${DEVICE_NAME}.crt"

# Verify it's a valid certificate
if ! openssl x509 -in "$CLIENT_DIR/${DEVICE_NAME}.crt" -noout 2>/dev/null; then
    echo ""
    echo "✗ ERROR: Invalid certificate provided"
    rm -rf "$CLIENT_DIR"
    exit 1
fi

echo ""
echo "✓ Certificate saved successfully!"

# Create PKCS#12 bundle
echo ""
echo "Step 4: Creating .p12 bundle for device installation..."
echo "(You'll be prompted for an export password - can be empty or set for extra security)"
openssl pkcs12 -export \
  -out "$CLIENT_DIR/${DEVICE_NAME}.p12" \
  -inkey "$CLIENT_DIR/${DEVICE_NAME}.key" \
  -in "$CLIENT_DIR/${DEVICE_NAME}.crt" \
  -name "$DEVICE_NAME"

chmod 644 "$CLIENT_DIR/${DEVICE_NAME}.p12"

echo ""
echo "=========================================="
echo "✓ Client certificate created successfully!"
echo "=========================================="
echo ""
echo "Files created in: $CLIENT_DIR/"
echo "  ${DEVICE_NAME}.key - Private key (KEEP THIS SECURE)"
echo "  ${DEVICE_NAME}.csr - Certificate signing request"
echo "  ${DEVICE_NAME}.crt - Signed certificate"
echo "  ${DEVICE_NAME}.p12 - PKCS#12 bundle (install this on your device)"
echo ""
echo "Next steps:"
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
