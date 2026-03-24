#!/bin/bash
# Deploy Celery workers to GCP Compute Engine VM (Free Tier e2-micro)

set -e

PROJECT_ID="memoryful"
ZONE="us-central1-a"
VM_NAME="celery-worker-free"
MACHINE_TYPE="e2-micro"

echo "Creating free tier e2-micro VM for Celery workers..."

gcloud compute instances create $VM_NAME \
  --project=$PROJECT_ID \
  --zone=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --image-family=cos-stable \
  --image-project=cos-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-standard \
  --scopes=cloud-platform \
  --metadata=google-logging-enabled=true \
  --tags=celery-worker

echo "VM created successfully!"
echo ""
echo "Next steps:"
echo "1. SSH into the VM: gcloud compute ssh $VM_NAME --zone=$ZONE"
echo "2. Set up docker-compose alias (Container-Optimized OS):"
echo "   echo 'alias docker-compose=\"docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v \\\"\\\$PWD:\\\$PWD\\\" -w \\\"\\\$PWD\\\" docker/compose:latest\"' >> ~/.bashrc"
echo "   source ~/.bashrc"
echo "3. Clone your repository: git clone https://github.com/YOUR_USERNAME/memoryful-backend.git"
echo "4. cd memoryful-backend"
echo "5. Create .env file: cp .env.prod .env and edit with your values"
echo "6. Add GCP service account JSON to secrets/service-account.json"
echo "7. Deploy: docker-compose -f docker/docker-compose.celery.yml --env-file=.env up -d"
