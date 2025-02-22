# FPL Data Munger

## Overview

This project takes fantasy league data provided by the Fantasy Premier League API and converts it into a CSV format suitable for import into Excel, Grafana, etc.

The 'league', in this case, is the league you are in with your friends - not the actual English Premier League.

## Currently supported

1. Draft Fantasy / head-to-head
~~2. Draft Fantasy / points~~
~~3. Main Fantasy / head-to-head~~
~~4. Main Fantasy / points~~


## Steps

1. Add repository variables `AWS_ACCOUNT_ID` (numeric) and `AWS_REGION` (string) to repository settings in GitHub.
2. Follow AWS guide to setting up IAM roles to connect to GitHub Actions: https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/
