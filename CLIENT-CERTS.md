# Client Certificate Authentication with Cloudflare mTLS

This document describes how to set up client certificate authentication for services on itsshedtime.com using Cloudflare mTLS.

## Architecture

This setup uses two layers of mTLS authentication:

**Layer 1: End Users → Cloudflare (Cloudflare-Managed mTLS)**
1. Cloudflare Access generates and manages client certificates for your users
2. Users download certificates from Cloudflare and install on their devices
3. Cloudflare validates certificates when users connect
4. Only authenticated users can proceed

**Layer 2: Cloudflare → Origin Server (Authenticated Origin Pulls)**
5. Cloudflare presents a client certificate (signed by your CA) to nginx
6. nginx validates Cloudflare's certificate against your CA
7. This prevents direct access to your origin server bypassing Cloudflare

This provides end-to-end authentication with Cloudflare managing user certificates and your CA protecting the origin.

## Initial Setup

### 1. Configure Cloudflare Access Application with mTLS

Set up the Cloudflare Access application which will generate and validate client certificates:

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Access** > **Applications**
3. Click **Add an application** > **Self-hosted**
4. Configure the application:
   - **Application name**: Home Assistant
   - **Session duration**: 24 hours (or your preference)
   - **Application domain**: `homeassistant.itsshedtime.com`
5. Add a policy:
   - **Policy name**: mTLS Required
   - **Action**: Allow
   - **Rule type**: Include
   - **Selector**: mTLS Certificate (Cloudflare will manage these)
6. Save the application

### 2. Initialize Your Certificate Authority (for Authenticated Origin Pulls)

Create a private CA for securing connections from Cloudflare to your origin server:

```bash
./scripts/init-ca.sh
```

You'll be prompted to:
1. Create a passphrase for the CA private key (SAVE THIS SECURELY!)
2. The script creates:
   - `pki/ca/ca.key` - CA private key (encrypted, KEEP SECURE)
   - `pki/ca/ca.crt` - CA certificate (deployed to your server)
   - `pki/ca/serial` - Certificate serial number tracker
   - `pki/ca/index.txt` - Certificate database

**IMPORTANT:** Back up the `pki/` directory securely. This CA is only for Authenticated Origin Pulls.

### 3. Upload Origin Certificate to Cloudflare

Create and upload a certificate that Cloudflare will present to your nginx server:

```bash
# Set required environment variables
export CLOUDFLARE_ZONE_ID='your-zone-id'
export CLOUDFLARE_EMAIL='your-email@example.com'
export CLOUDFLARE_API_KEY='your-global-api-key'

# Create and upload the origin certificate
./scripts/upload-cloudflare-origin-cert.sh homeassistant.itsshedtime.com
```

**Finding these credentials:**
- **Zone ID**: Cloudflare Dashboard > Select your domain > Overview (right sidebar)
- **Global API Key**: My Profile > API Tokens > Global API Key > View

### 4. Enable Authenticated Origin Pulls in Cloudflare

Enable Authenticated Origin Pulls and configure the hostname:

```bash
# Set required environment variables (same as step 3)
export CLOUDFLARE_ZONE_ID='your-zone-id'
export CLOUDFLARE_EMAIL='your-email@example.com'
export CLOUDFLARE_API_KEY='your-global-api-key'

# Enable for homeassistant
./scripts/enable-cloudflare-origin-pulls.sh homeassistant.itsshedtime.com
```

This script will:
1. Find the uploaded certificate
2. Configure the hostname to use it
3. Enable Authenticated Origin Pulls for that hostname

### 5. Deploy nginx Configuration

Deploy the CA certificate and nginx configuration to your origin server:

```bash
ansible-playbook --inventory hosts playbook.yml --verbose
```

This configures nginx to validate client certificates presented by Cloudflare.

### 6. Generate Client Certificates

Generate a client certificate for each device:

```bash
./scripts/generate-cloudflare-client-cert.sh <device-name>
```

**Example:**
```bash
./scripts/generate-cloudflare-client-cert.sh andrews-iphone
```

The script will:
1. Generate a private key (kept secure on your machine)
2. Generate and display a CSR
3. Show instructions for submitting the CSR to Cloudflare
4. Wait for you to paste back the signed certificate
5. Create a .p12 bundle ready for installation

**Steps to follow:**
1. Run the script - it will display a CSR
2. Go to: Cloudflare Dashboard > SSL/TLS > Edge Certificates > Client Certificates
3. Click "Create Certificate" > "Use my CSR"
4. Paste the CSR and set validity (e.g., 10 years)
5. Click "Create"
6. Copy the signed certificate from Cloudflare
7. Return to the terminal and press Enter
8. Paste the certificate (Ctrl+D when finished)

All files are saved to `pki/cloudflare-clients/<device-name>/`

### 7. Install Client Certificates on Devices

See the "Installing Client Certificates on Devices" section below for platform-specific instructions.

## Installing Client Certificates on Devices

The `generate-csr.sh` script creates a `.p12` file ready for installation. Transfer this file to your device and follow the platform-specific instructions below.

### iOS/iPadOS

1. Transfer the `.p12` file to your device (AirDrop, email, etc.)
2. Tap the file to open it
3. Follow the prompts to install the certificate
4. Go to Settings > General > VPN & Device Management
5. Tap the certificate and tap "Install"
6. Enter your device passcode
7. Enter the .p12 export password if you set one
8. Visit https://homeassistant.itsshedtime.com in Safari
9. Safari will prompt you to select a certificate - choose the one you just installed

### macOS

1. Double-click the `.p12` file
2. Keychain Access will open
3. Enter the .p12 export password if you set one
4. Enter your Mac password to allow the import
5. Visit https://homeassistant.itsshedtime.com in Safari or Chrome
6. Your browser will prompt you to select a certificate

### Android

1. Transfer the `.p12` file to your device
2. Go to Settings > Security > Encryption & credentials > Install a certificate > VPN & app user certificate
3. Browse to the `.p12` file
4. Enter the .p12 export password if you set one
5. Give the certificate a name (e.g., "Home Assistant")
6. Visit https://homeassistant.itsshedtime.com in Chrome
7. Chrome will prompt you to select a certificate

### Linux (Firefox)

1. Open Firefox
2. Go to Preferences > Privacy & Security > Certificates > View Certificates
3. Click "Your Certificates" tab
4. Click "Import"
5. Select the `.p12` file
6. Enter the .p12 export password if you set one
7. Visit https://homeassistant.itsshedtime.com
8. Firefox will prompt you to select a certificate

### Linux (Chrome/Chromium)

1. Open Chrome/Chromium
2. Go to Settings > Privacy and security > Security > Manage certificates
3. Click "Import"
4. Select the `.p12` file
5. Enter the .p12 export password if you set one
6. Visit https://homeassistant.itsshedtime.com
7. Chrome will prompt you to select a certificate

### Windows

1. Double-click the `.p12` file
2. Select "Current User" and click Next
3. Click Next to confirm the file path
4. Enter the .p12 export password if you set one
5. Select "Automatically select the certificate store based on the type of certificate"
6. Click Next, then Finish
7. Visit https://homeassistant.itsshedtime.com in your browser
8. Your browser will prompt you to select a certificate

## Certificate Management

### Viewing Certificates

**Local certificates:**
```bash
ls -la pki/cloudflare-clients/
```

View certificate details:
```bash
openssl x509 -in pki/cloudflare-clients/<device-name>/<device-name>.crt -noout -text
```

**Cloudflare-managed certificates:**
1. Go to Cloudflare Dashboard > SSL/TLS > Edge Certificates > Client Certificates
2. View all issued certificates and their expiration dates

### Revoking Certificates

If a device is lost or compromised:

**Via Cloudflare Dashboard:**
1. Go to Cloudflare Dashboard > SSL/TLS > Edge Certificates > Client Certificates
2. Find the certificate (identified by serial number or Common Name)
3. Click **Revoke**
4. Confirm the revocation

**Via API:**
```bash
# Get the certificate ID first
curl -X GET "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/client_certificates" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"

# Revoke using the certificate ID
curl -X DELETE "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/client_certificates/<cert-id>" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
```

The certificate will be immediately invalid and the user will lose access.

### Renewing Certificates

Client certificates can be renewed before expiration:

1. Before the certificate expires, delete the old certificate directory:
   ```bash
   rm -rf pki/cloudflare-clients/<device-name>
   ```

2. Generate a new certificate:
   ```bash
   ./scripts/generate-cloudflare-client-cert.sh <device-name>
   ```

3. Install the new `.p12` file on the device

4. Optionally revoke the old certificate in Cloudflare once the new one is working

### Rotating the Origin CA

If the origin CA is compromised or you want to rotate it (recommended every 5-10 years):

1. Back up the old CA:
   ```bash
   mv pki/ca pki/ca.old.$(date +%Y%m%d)
   ```

2. Initialize a new CA:
   ```bash
   ./scripts/init-ca.sh
   ```

3. Upload new origin certificate to Cloudflare:
   ```bash
   ./scripts/upload-cloudflare-origin-cert.sh homeassistant.itsshedtime.com
   ```

4. Deploy the new CA to the server:
   ```bash
   ansible-playbook --inventory hosts playbook.yml --verbose
   ```

Note: This only affects Authenticated Origin Pulls. End-user certificates are managed by Cloudflare and are not affected.

## Security Best Practices

1. **Protect the CA Private Key**: The `pki/ca/ca.key` file is encrypted with a passphrase. Keep this passphrase secure (password manager recommended).

2. **Back Up Regularly**: Back up the `pki/` directory to a secure location (encrypted external drive, cloud storage with encryption).

3. **Use Strong Export Passwords**: When creating .p12 bundles, use a strong export password if the file will be transmitted over insecure channels.

4. **Delete Certificate Files After Installation**: Once installed on a device, delete certificate and key files from any temporary locations.

5. **Monitor Certificate Expiration**: Keep track of expiration dates in Cloudflare Zero Trust Dashboard and renew proactively.

6. **Device-Specific Certificates**: Issue a separate certificate for each device in Cloudflare. This allows you to revoke access for a single device without affecting others.

7. **Don't Commit Private Keys**: The `.gitignore` is configured to prevent committing private keys, but always double-check before committing.

## Troubleshooting

### "Certificate Required" or Access Denied Error

**Symptom**: Cloudflare shows an access denied page or certificate error

**Solutions**:
- Verify the certificate is installed on your device (see installation instructions above)
- Check that the certificate hasn't expired (check in Cloudflare Zero Trust Dashboard)
- Verify the Access policy is configured correctly and includes the mTLS rule
- Check that the certificate wasn't revoked
- Try a different browser (some browsers handle client certificates differently)
- On mobile, use Safari (iOS) or Chrome (Android) as they have better client cert support

### Certificate Not Prompted in Browser

**Symptom**: Browser doesn't ask which certificate to use

**Solutions**:
- Verify certificate is installed in the correct store (Current User on Windows, System keychain on macOS)
- Restart the browser completely
- Check certificate is valid using Cloudflare dashboard
- Try accessing from an incognito/private window

### Origin Server Connection Issues

**Symptom**: Works with client cert but gets 502/503 errors

**Solutions**:
- Verify Authenticated Origin Pulls is enabled in Cloudflare
- Check nginx configuration on origin server: `sudo nginx -t`
- Verify CA certificate exists: `sudo ls -la /etc/nginx/client-certs/`
- Check nginx error logs: `sudo tail -f /var/log/nginx/error.log`

### Verify Cloudflare Configuration

Check that everything is configured in Cloudflare:

1. **Access Application**: Zero Trust Dashboard > Access > Applications (verify homeassistant.itsshedtime.com exists)
2. **mTLS Certificates**: Zero Trust Dashboard > Access > Service Auth > mTLS Certificates (verify certificates are issued)
3. **Authenticated Origin Pulls**: Cloudflare Dashboard > SSL/TLS > Origin Server (verify enabled)
4. **Origin Certificate**: Cloudflare Dashboard > SSL/TLS > Origin Server > Origin Certificates (verify uploaded)

## Adding Client Certificate Authentication to Other Services

To protect other services with the same setup:

1. Create a new Access Application in Cloudflare:
   - Go to Zero Trust Dashboard > Access > Applications
   - Add an application for the new hostname (e.g., `myapp.itsshedtime.com`)
   - Use the same mTLS policy

2. Upload an origin certificate for the new hostname:
   ```bash
   ./scripts/upload-cloudflare-origin-cert.sh myapp.itsshedtime.com
   ```

3. Enable Authenticated Origin Pulls for the new hostname (if using per-hostname configuration)

4. Users with existing Cloudflare-issued certificates will automatically have access to the new service

## Technical Details

### Certificate Specifications

**Origin Certificates (Your CA):**
- CA Key: RSA 4096-bit
- CA Validity: 10 years
- Client Key: RSA 2048-bit
- Client Validity: 2 years
- Subject: CN=cloudflare-origin
- Extensions:
  - Key Usage: Digital Signature, Key Encipherment
  - Extended Key Usage: Client Authentication
  - Basic Constraints: CA=FALSE

**End-User Certificates (Cloudflare-Managed):**
- Managed entirely by Cloudflare
- Downloaded from Cloudflare Zero Trust Dashboard
- Validity: Up to 10 years (configured when creating)

### File Locations

**Local (repository):**
- `pki/ca/ca.key` - CA private key (git-ignored)
- `pki/ca/ca.crt` - CA certificate (committed to git)
- `pki/clients/cloudflare-origin/` - Certificate Cloudflare presents to nginx (git-ignored)
- `pki/cloudflare-clients/<device-name>/` - End-user device certificates (git-ignored)
- `scripts/init-ca.sh` - CA initialization script
- `scripts/generate-cloudflare-client-cert.sh` - Generate client certificates (interactive CSR workflow)
- `scripts/issue-client-cert.sh` - Client certificate issuance script (used for origin cert)
- `scripts/upload-cloudflare-origin-cert.sh` - Create and upload origin certificate
- `scripts/enable-cloudflare-origin-pulls.sh` - Enable Authenticated Origin Pulls for a hostname

**Note:** Scripts that interact with Cloudflare require environment variables: `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_EMAIL`, and `CLOUDFLARE_API_KEY`.

**Remote (server):**
- `/etc/nginx/client-certs/ca.crt` - CA certificate for validating Cloudflare
- `/etc/nginx/sites-enabled/homeassistant` - Home Assistant nginx config with client cert validation

**Cloudflare:**
- End-user certificates managed in Zero Trust Dashboard
- Origin client certificate uploaded for Authenticated Origin Pulls
- Access policies configured for protected applications
