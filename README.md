<img width="1179" alt="image" src="https://github.com/TheFirewall-code/TheFirewall-Secrets-SCA/blob/3a62498a9e124657cc6d99685ba7552a1e9529c7/static/Thefirewall-cover-image.png"/>

<div align="center">
<br>

<a href="https://docs.thefirewall.org"><img src="https://img.shields.io/badge/Documentation-%23000000.svg?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTQgMTkuNUEyLjUgMi41IDAgMCAxIDYuNSAxN0gyMCIvPjxwYXRoIGQ9Ik02LjUgMkgyMHYyMEg2LjVBMi41IDIuNSAwIDAgMSA0IDE5LjVWNC41QTIuNSAyLjUgMCAwIDEgNi41IDJ6Ii8+PC9zdmc+"></a>&nbsp;&nbsp;<a href="https://blogs.thefirewall.org/"><img src="https://img.shields.io/badge/Blogs-%23000000.svg?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBhdGggZD0iTTEyIDE5bDctNyAzIDMtNyA3LTMtM3oiLz48cGF0aCBkPSJNMTggMTNsLTEuNS03LjVMMiAybDMuNSAxNC41TDEzIDE4bDUtNXoiLz48cGF0aCBkPSJNMiAybDcuNTg2IDcuNTg2Ii8+PHBhdGggZD0iTTExIDExbC00IDQiLz48L3N2Zz4="></a>&nbsp;&nbsp;<a href="https://discord.gg/jD2cEy2ugg"><img src="https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white"></a>&nbsp;&nbsp;<a href="mailto:support@thefirewall.org"><img src="https://img.shields.io/badge/Support-%23000000.svg?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNmZmZmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0ibHVjaWRlIGx1Y2lkZS1oZWxwaW5nLWhhbmQiPjxwYXRoIGQ9Ik0yIDExYTEwIDEwIDAgMSAwIDIwIDAgMTAgMTAgMCAxIDAtMjAgMHoiLz48cGF0aCBkPSJtMTAgOSA0LTQgNC40IDQuNGEyLjEgMi4xIDAgMCAxIC4zIDIuNyAxLjkgMS45IDAgMCAxLTMgLjNMMTMgOWwtMy0zeiIvPjxwYXRoIGQ9Im05IDEzLTQgNCA0LjQgNC40YTIuMSAyLjEgMCAwIDAgMi43LjMgMS45IDEuOSAwIDAgMCAuMy0zbC0yLjctMi43LTMtM3oiLz48L3N2Zz4="></a>

</div>

Welcome to **The Firewall Appsec Platform** for **Secrets Scanning** and **Software Composition Analysis (SCA)**. This suite aims to provide security scanning tools to enhance your organisation's security posture.

## Table of Contents

- [Installation](#installation)
  - [Docker Installation (with Docker Compose)](#docker-installation-with-docker-compose)
  - [AWS CloudFormation Installation](#aws-cloudFormation-installation)
  - [AWS Marketplace Installation](#aws-marketplace-installation)
- [Usage](#usage)
- [Privacy Policy](#privacy-policy)
- [Vulnerability Disclosure Policy](#vulnerability-disclosure-policy)
- [Licence](#licence)
- [Support](#support)

## Installation

You have two installation options: Docker and AWS CloudFormation.

### Docker Installation (with Docker Compose)

1. **Clone the Repository**  
   First, clone this repository to your local machine:
   ```bash
   git clone https://github.com/TheFirewall-code/TheFirewall-Secrets-SCA.git
   cd TheFirewall-Secrets-SCA
   ```

2. **Set up Docker Compose**  
   In this repo, you’ll find a `docker-compose.yml` file to help you set up both tools with minimal configuration.

   Make sure you have Docker and Docker Compose installed. If not, you can get them [here](https://docs.docker.com/get-docker/).

3. **Run Docker Compose**  
   Start the services by running:
   ```bash
   docker-compose up -d
   ```

4. **Access the Tools**  
   Once the containers are up and running, you can access the services on the following ports (check the `docker-compose.yml` for specific mappings):
   - **TheFirewall Platform**: `http://localhost:3000`

5. **Stopping the Services**  
   To stop the services, simply run:
   ```bash
   docker-compose down
   ```


### AWS CloudFormation Installation

1. **Access the CloudFormation Template**  
   Open the AWS CloudFormation console and click on **Create stack**.  
   Use the following template URL:
   ```bash
   https://cf-templates-1ugfe9jf0z24o-ap-south-1.s3.ap-south-1.amazonaws.com/template-1739983635479.yaml
   ```
   
3. **Launch the CloudFormation Stack**  
- Choose **"Template is ready"** and select **"Amazon S3 URL"**.  
- Paste the URL above and click **Next**.  
- Provide a **Stack Name** and any required parameters.  
- Click **Next**, configure stack options if needed, and proceed.  
- Acknowledge any IAM permissions required and click **Create Stack**.

3. **Wait for Deployment**  
- The deployment process will take a few minutes.  
- Monitor the progress in the **CloudFormation Stacks** section.  
- Once complete, the status will change to `CREATE_COMPLETE`.

4. **Access the Tools**  
- After the stack is deployed, go to the **Outputs** tab.  
- Find the endpoint URLs for accessing the deployed services.

5. **Deleting the Stack**  
If you want to remove the deployment, delete the stack by selecting it in CloudFormation and clicking **Delete**.


   
### AWS Marketplace Installation

Alternatively, you can install **The Firewall Appsec Platform** directly via the [AWS Marketplace](https://aws.amazon.com/marketplace). Follow these steps:

1. Go to the [The Firewall Appsec Platform](https://aws.amazon.com/marketplace/pp/prodview-sxhlfl6vz6rma) on AWS Marketplace.
2. **Subscribe for Free**: Click on the "Subscribe" button to get started.
3. Once subscribed, **deploy the app** using the AWS Management Console.
4. You can now manage and use both tools through your AWS environment.

> **Note:** The AWS Marketplace deployment gives you an easy way to set up The Firewall Appsec Platform in the cloud, with minimal setup needed on your local machine.

---

## Usage

After installation, you can begin using the tools:

- **Secrets Scanning Tool**: This tool scans your codebase for sensitive information like passwords, API keys, and other secrets.
- **SCA Tool**: The Software Composition Analysis tool analyzes your project’s dependencies for vulnerabilities, ensuring you know the security risks of your third-party libraries.

For detailed usage instructions for each tool, refer to the respective documentation [over here](https://docs.thefirewall.org).


## Privacy Policy

We take your privacy seriously. When you register for a Community License:
* We only collect your email address
* Your email is used solely for license generation and critical security notifications
* We never share your information with third parties
* You can request data deletion at any time
Read our full Privacy Policy for detailed information about data handling and protection.

## Vulnerability Disclosure Policy

At Firewall, we take the security of our systems seriously. We value the input of security researchers and the broader community in helping to maintain high security standards. This policy sets out our commitments and guidelines for responsible vulnerability disclosure. Read our [full Policy](https://www.thefirewall.org/vdp) for detailed information about vulnerability disclosure program.

## Licence
The Firewall offers a Community License that is completely free and includes:

* Unlimited number of assets
* Unlimited users
* All features and capabilities
* Regular updates

No hidden costs, no usage limits, no user restrictions. Just enter your email and get full access to enterprise-grade security.


## Support

We're here to help you succeed with The Firewall platform!

📚 Documentation: https://docs.thefirewall.org  

📚 Blogs: https://blogs.thefirewall.org 

💬 Community: [[Discord Community Link](https://discord.gg/jD2cEy2ugg)]  

📧 Email: support@thefirewall.org

📞 Call: +91-8057599291, +91-8194015800

 Questions? Choose any channel - we're responsive on all of them!


