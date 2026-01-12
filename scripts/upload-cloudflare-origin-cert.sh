#!/bin/bash
set -e

# Create and upload a client certificate for Cloudflare Authenticated Origin Pulls
# This certificate is presented by Cloudflare when connecting to your origin server

CA_DIR="$(cd "$(dirname "$0")/.." && pwd)/pki/ca"
CLIENTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/pki/clients"
CLIENT_DIR="$CLIENTS_DIR/cloudflare-origin"
DEVICE_NAME="cloudflare-origin"
HOSTNAME="${1:-homeassistant.itsshedtime.com}"

# Check if CA exists
if [ ! -f "$CA_DIR/ca.key" ] || [ ! -f "$CA_DIR/ca.crt" ]; then
    echo "ERROR: Certificate Authority not found. Run ./scripts/init-ca.sh first."
    exit 1
fi

# Check for required environment variables
if [ -z "$CLOUDFLARE_ZONE_ID" ] || [ -z "$CLOUDFLARE_EMAIL" ] || [ -z "$CLOUDFLARE_API_KEY" ]; then
    echo "ERROR: Required environment variables not set"
    echo ""
    echo "Please set the following environment variables:"
    echo "  export CLOUDFLARE_ZONE_ID='your-zone-id'"
    echo "  export CLOUDFLARE_EMAIL='your-email@example.com'"
    echo "  export CLOUDFLARE_API_KEY='your-global-api-key'"
    echo ""
    echo "You can find these in your Cloudflare dashboard:"
    echo "  - Zone ID: Overview page of your domain"
    echo "  - Global API Key: My Profile > API Tokens > Global API Key > View"
    exit 1
fi

# Check if Cloudflare origin client cert already exists
if [ ! -d "$CLIENT_DIR" ]; then
    echo "Creating client certificate for Cloudflare Authenticated Origin Pulls..."
    echo ""

    # Issue the certificate
    "$( dirname "$0")/issue-client-cert.sh" "$DEVICE_NAME"

    echo ""
    echo "Certificate created successfully."
else
    echo "Certificate for Cloudflare origin already exists at $CLIENT_DIR"
fi

echo ""
echo "Uploading certificate to Cloudflare for hostname: $HOSTNAME"
echo ""

# Prepare certificate and key for JSON
MYCERT="$(cat "$CLIENT_DIR/${DEVICE_NAME}.crt" | perl -pe 's/\r?\n/\\n/' | sed -e 's/..$//')"
MYKEY="$(cat "$CLIENT_DIR/${DEVICE_NAME}.key" | perl -pe 's/\r?\n/\\n/' | sed -e 's/..$//')"

# Create request body
request_body=$(cat <<EOF
{
  "certificate": "$MYCERT",
  "private_key": "$MYKEY",
  "bundle_method": "ubiquitous"
}
EOF
)

# Upload to Cloudflare for Authenticated Origin Pulls
response=$(curl --silent \
  "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/origin_tls_client_auth" \
  --header "Content-Type: application/json" \
  --header "X-Auth-Email: $CLOUDFLARE_EMAIL" \
  --header "X-Auth-Key: $CLOUDFLARE_API_KEY" \
  --data "$request_body")

# Check if successful
if echo "$response" | grep -q '"success":true'; then
    echo "✓ Certificate uploaded successfully to Cloudflare!"
    echo ""
    cert_id=$(echo "$response" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "Certificate ID: $cert_id"
    echo "Hostname: $HOSTNAME"
    echo ""
    echo "Next steps:"
    echo "1. Enable Authenticated Origin Pulls for $HOSTNAME in Cloudflare dashboard:"
    echo "   SSL/TLS > Origin Server > Authenticated Origin Pulls"
    echo "2. Deploy the CA certificate to your nginx server:"
    echo "   ansible-playbook --inventory hosts playbook.yml --verbose"
    echo "3. Cloudflare will now present this client certificate when connecting to your origin"
else
    echo "✗ Failed to upload certificate to Cloudflare"
    echo ""
    echo "Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    exit 1
fi
