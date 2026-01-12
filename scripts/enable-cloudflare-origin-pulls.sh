#!/bin/bash
set -e

# Enable Authenticated Origin Pulls for a hostname
# Usage: ./enable-cloudflare-origin-pulls.sh <hostname>

HOSTNAME="${1:-homeassistant.itsshedtime.com}"

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

echo "Enabling Authenticated Origin Pulls for: $HOSTNAME"
echo ""

# Get the certificate ID
echo "Step 1: Finding uploaded certificate..."
cert_response=$(curl --silent \
  "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/origin_tls_client_auth/hostnames/certificates" \
  --header "Content-Type: application/json" \
  --header "X-Auth-Email: $CLOUDFLARE_EMAIL" \
  --header "X-Auth-Key: $CLOUDFLARE_API_KEY")

# Extract certificate ID using Python
cert_id=$(echo "$cert_response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['result'][0]['id'] if data.get('success') and data.get('result') else '')" 2>/dev/null)

if [ -z "$cert_id" ]; then
    echo "✗ ERROR: No certificate found"
    echo ""
    echo "Response from Cloudflare:"
    echo "$cert_response" | python3 -m json.tool 2>/dev/null || echo "$cert_response"
    echo ""
    echo "Please run ./scripts/upload-cloudflare-origin-cert.sh first"
    exit 1
fi

echo "✓ Found certificate ID: $cert_id"
echo ""

# Enable Authenticated Origin Pulls for the hostname
echo "Step 2: Configuring hostname to use certificate..."

# Construct JSON payload with proper structure
json_payload='{"config":[{"hostname":"'"$HOSTNAME"'","cert_id":"'"$cert_id"'","enabled":true}]}'

response=$(curl --silent -X PUT \
  "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/origin_tls_client_auth/hostnames" \
  --header "Content-Type: application/json" \
  --header "X-Auth-Email: $CLOUDFLARE_EMAIL" \
  --header "X-Auth-Key: $CLOUDFLARE_API_KEY" \
  --data "$json_payload")

# Check if successful
if echo "$response" | grep -q '"success":true'; then
    echo "✓ Authenticated Origin Pulls enabled successfully!"
    echo ""
    echo "Configuration:"
    echo "  Hostname: $HOSTNAME"
    echo "  Certificate ID: $cert_id"
    echo ""
    echo "The origin certificate is now active. Cloudflare will present this certificate"
    echo "when connecting to your nginx server."
    echo ""
    echo "Next steps:"
    echo "1. Verify nginx is configured with client certificate validation"
    echo "2. Test the connection to $HOSTNAME"
else
    echo "✗ Failed to enable Authenticated Origin Pulls"
    echo ""
    echo "Response:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    exit 1
fi
