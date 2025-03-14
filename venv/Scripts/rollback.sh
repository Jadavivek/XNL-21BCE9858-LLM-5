#!/bin/bash

echo "Rolling back AWS Lambda..."
aws lambda update-function-code --function-name my-llm-app --zip-file fileb://previous_version.zip

echo "Rolling back GCP App Engine..."
gcloud app versions migrate previous-version

echo "Rollback complete."

chmod +x scripts/rollback.sh
