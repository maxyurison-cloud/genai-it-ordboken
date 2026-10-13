# IT-ordboken – GenAI app on AWS

A small web app that explains IT terms in simple Swedish using Google Gemini (generative AI).
The user types a term (e.g. *DNS*, *VLAN*), the app sends it to the Gemini API and shows the answer.

## Architecture

```
Browser --HTTP:80--> EC2 (Amazon Linux 2023)
                       nginx (reverse proxy)
                         -> gunicorn + Flask app (127.0.0.1:5000)
                              -> Gemini API (HTTPS)
```

- **Infrastructure:** Terraform (based on my Level 3 web server): EC2 t3.micro, security group with only port 80 open.
- **Configuration & deploy:** cloud-init user data installs nginx and Python, copies the app and starts it as a systemd service.
- **AI:** Google Gemini API. The app first tries the fast `gemini-flash-lite-latest`; if it is overloaded (HTTP 503/429) or times out, it automatically falls back to `gemini-flash-latest`.

## Security of the API key

The key is **never** stored in this repository.
Terraform asks for it at `terraform apply` (`sensitive` variable) and writes it only to `/etc/app.env` on the server (readable by root only).
`.gitignore` excludes `*.tfvars`, `*.tfstate` and `.env`.

## Deploy

```bash
cd terraform
terraform init
terraform apply      # paste the Gemini API key when asked
```

Open the `app_url` from the output after ~3 minutes.

## Tear down

```bash
terraform destroy
```

## Files

| Path | Purpose |
|---|---|
| `app/app.py` | Flask app: web page + `/api/forklara` that calls Gemini |
| `app/requirements.txt` | Python dependencies |
| `terraform/*.tf` | AWS infrastructure |
| `terraform/user-data.sh.tftpl` | Server setup script (cloud-init) |
