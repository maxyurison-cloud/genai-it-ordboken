# Project documentation – IT-ordboken (GenAI app on AWS)

**Author:** Maksym Kyselov
**Repository:** https://github.com/maxyurison-cloud/genai-it-ordboken

## Project summary

IT-ordboken ("the IT dictionary") is a small web application that explains IT terms in simple Swedish.
The user types a term such as *DNS*, *VLAN* or *firewall*, and a generative AI model (Google Gemini) writes a short explanation with a concrete example.

The idea comes from my own situation: I study to become an IT technician (IT-driftteknikare) in Swedish, which is not my first language. A tool that explains technical terms in plain Swedish is useful for students like me.

The generative AI is the core of the application. Without the AI model, the app has no content at all.

**Final architecture:**

```
User's browser --HTTP (port 80)--> AWS EC2 (Amazon Linux 2023, t3.micro)
                                     nginx (reverse proxy, from Level 3)
                                       -> gunicorn + Python Flask app
                                            -> Google Gemini API (HTTPS)
```

All infrastructure is created with Terraform. The server installs and starts everything by itself at first boot (cloud-init user data).

---

## Phase 1: Research

### Information gathering

- I read the assignment and listed the hard requirements: a GenAI feature at the centre of the app, hosting in AWS with a public IP, reuse of my Level 3 web server, documentation, a video and a GitHub repository.
- I compared AI providers mentioned in the assignment: OpenAI, Anthropic Claude, Google Gemini and AWS Bedrock.
- I read about the Gemini Developer API and Google AI Studio (how to create a key, free tier, model names).
- I reviewed my own Level 3 project (Terraform + EC2 + nginx + automated deploy with user data), since the assignment says to build on it.

### Choice of tools and technologies

| Area | Choice | Reason |
|---|---|---|
| AI model | Google Gemini API | Free tier without a payment card, simple REST API, key created in two minutes in Google AI Studio |
| Backend | Python + Flask | Very small amount of code for one web page and one API endpoint |
| App server | gunicorn | Standard way to run a Flask app in production instead of the development server |
| Web server | nginx as reverse proxy | Same web server as in my Level 3 project |
| Infrastructure | Terraform | Reused from Level 3; the whole environment can be created and destroyed with one command |
| Server setup | cloud-init user data | Same automation idea as Level 3: no manual login to the server |
| Version control | Git + GitHub | Required by the assignment |

### Planning

I split the work into small steps and tested each step before the next one:

1. Get an API key and test that the AI answers.
2. Write the app.
3. Adapt the Level 3 Terraform code and deploy to AWS.
4. Test the app online.
5. Publish the code on GitHub.
6. Write documentation and record the video.
7. Destroy the AWS resources and delete the API key after grading.

### Problems and solutions in the research phase

- **Problem:** At first it was unclear why I needed a separate AI API when I already use an AI chat assistant.
  **Solution:** I learned the difference between a chat product and an API. A web application running on a server cannot use a chat window – it needs an API key and sends requests from code.
- **Problem:** Information about free AI tiers is changing quickly, and different sources said different things (some said new users must prepay).
  **Solution:** I tested it in practice: I created the key in Google AI Studio and checked that it worked without a payment card.
- **Problem:** The requirement "use Level 3" was not detailed.
  **Solution:** I interpreted it as: reuse the same pattern – Terraform for the EC2 instance, nginx as web server and fully automated deploy through user data.

---

## Phase 2: Implementation

### How the work started

I started with the application itself, because it is the core of the project. The app has two parts in one file (`app/app.py`):

- `/` – a simple web page in Swedish with an input field and a button.
- `/api/forklara` – receives the term, sends it to Gemini together with a short instruction ("explain this IT term in simple Swedish, max 6 sentences, give an example") and returns the answer.

The app was tested locally before deploying: the page loads, empty input is rejected and the app reports clearly when the API key is missing.

### Infrastructure

I created a new Terraform project based on Level 3 (`terraform/`):

- `main.tf` – finds the latest Amazon Linux 2023 image automatically, uses the default VPC, creates a security group that only allows HTTP (port 80) and creates the EC2 instance.
- `user-data.sh.tftpl` – the setup script that runs at first boot: installs nginx and Python, copies the app, installs the Python packages, starts the app as a systemd service and configures nginx to forward port 80 to the app.
- `variables.tf` – the API key is a `sensitive` variable without a default value, so Terraform asks for it at `terraform apply`.
- `outputs.tf` – prints the public URL of the app.

### Security of the API key

The API key must never be published. I designed the project so that:

- the key is not written in any file in the repository;
- Terraform asks for it when I run `apply`, and it is placed only in `/etc/app.env` on the server (readable only by root);
- `.gitignore` excludes `*.tfstate`, `*.tfvars` and `.env`.

### Problems and solutions in the implementation phase

- **Problem:** My Level 3 Terraform code depended on hard-coded IDs (subnet, security group, key pair) from an old environment that I had already destroyed.
  **Solution:** I rewrote it so that Terraform creates or finds everything it needs by itself: a data source for the AMI, the default VPC and a new security group. Now the project works in any AWS account without manual changes.
- **Problem:** The first `terraform apply` was cancelled ("Apply cancelled") even though the plan was correct.
  **Solution:** The input for the hidden key prompt contained an extra line break, which was sent as an empty answer to the "yes" question. I pasted only the key, pressed Enter once and typed `yes` manually.
- **Problem:** The model name I had first planned to use might not be available any more.
  **Solution:** I used the model name that Google AI Studio itself shows in its example request (`gemini-flash-latest`), and tested it with `curl` from my computer.

---

## Phase 3: Completion and improvement

### Testing the whole solution

After deployment, the page loaded on the public IP, but every question returned the generic message *"AI-tjänsten svarade inte"* ("the AI service did not answer"). I tested step by step:

1. **Is the server working?** Yes – the page loaded through nginx.
2. **Does the API key work?** I sent the same request with `curl` from my own computer. Gemini answered "Hej!", so the key and the model were fine.
3. **So what fails on the server?** The error message in the app was too general to tell. I improved the error handling so that the app shows the real error code and message from Google (never the key).

After redeploying, the real reason became visible: **HTTP 503 – "This model is currently experiencing high demand"**. On the next try the request took longer than 30 seconds and failed with **ReadTimeout**.

### Improvements

- **Fallback between models:** the app first asks the fast `gemini-flash-lite-latest`. If it is overloaded (503/429), returns an error or times out, the app automatically tries `gemini-flash-latest`. If the key itself is invalid, it stops immediately instead of retrying.
- **Longer timeouts:** gunicorn and nginx timeouts were raised from 30–60 to 120 seconds, so the server does not cut the request while the app tries the second model.
- **Clear error messages:** the user sees what went wrong instead of a generic error.
- The fallback logic was tested with simulated answers (success, timeout, 503, invalid key) before deploying.

After this, the app answered correctly. Example answer for *DNS*:

> DNS står för Domain Name System och fungerar som internetets telefonbok. Istället för att komma ihåg krångliga IP-adresser med siffror, som till exempel 192.0.2.1, kan vi skriva en vanlig webbadress som svt.se. [...]

### Publishing

Before pushing to GitHub I checked `git status` to make sure that `terraform.tfstate` was not included. This file contains the API key in plain text, so publishing it would leak the key. The `.gitignore` worked as planned, and the repository contains only code and documentation.

### Problems and solutions in the completion phase

- **Problem:** The app worked locally but not on the server.
  **Solution:** I tested each layer separately (server, API key, app) and improved the error messages until the real cause was visible.
- **Problem:** The AI service was overloaded (503) and slow (timeout).
  **Solution:** Fallback to a second model and longer timeouts.
- **Problem:** Every redeploy creates a new server with a new public IP address, so the old browser tab stopped working ("Kunde inte nå servern").
  **Solution:** I always took the new address from `terraform output app_url`.

---

## Phase 4: Problems & solutions (summary)

| # | Problem | Solution |
|---|---|---|
| 1 | Unclear difference between AI chat and AI API | Learned that a server application needs an API key and REST calls |
| 2 | Conflicting information about free AI tiers | Tested in practice in Google AI Studio |
| 3 | Level 3 code depended on IDs from a destroyed environment | Terraform now creates/finds all resources itself |
| 4 | Risk of leaking the API key | Sensitive Terraform variable, key only on the server, `.gitignore`, check with `git status` before push |
| 5 | `terraform apply` cancelled because of an extra line break | Paste only the key, type `yes` manually |
| 6 | Generic error message hid the real problem | Better error handling that shows Google's error code and message |
| 7 | Gemini overloaded (HTTP 503) and slow (ReadTimeout) | Automatic fallback between two models, longer timeouts |
| 8 | New public IP after every redeploy | Use `terraform output app_url`; an Elastic IP would solve it permanently |

---

## Conclusion

### What I achieved

A working GenAI web application that runs in AWS and is reachable on a public IP address. The infrastructure is fully automated with Terraform: one command creates the whole environment, one command (`terraform destroy`) removes it. The code is published on GitHub without any secrets.

### What I learned

- How a web application calls a generative AI model through an API, and how this differs from using an AI chat.
- How to handle secrets (API keys) safely in Terraform and Git.
- How to reuse infrastructure code and make it independent of one specific environment.
- How to troubleshoot step by step, layer by layer, and why good error messages save time.
- That external AI services can be overloaded, so an application needs fallbacks and sensible timeouts.

I used an AI assistant (Claude) as support for writing code and troubleshooting, and I tested every step myself in my own AWS account.

### What could be improved

- **HTTPS** with a domain name and a certificate (for example Let's Encrypt), since the app now uses plain HTTP.
- **Elastic IP**, so the address does not change after a redeploy.
- **AWS Secrets Manager or SSM Parameter Store** for the API key instead of user data.
- **Rate limiting**, so nobody can use up the free AI quota.
- **Automated tests in GitHub Actions**, like the QA workflow in my Level 3 project.
