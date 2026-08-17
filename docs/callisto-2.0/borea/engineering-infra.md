# Quản lý hạ tầng — Borea

## Kiến trúc tổng quan
Borea chạy multi-cloud: AWS (primary, ap-southeast-1) + GCP (DR, asia-southeast1).
Microservices architecture với 25+ services.
Kubernetes (EKS) cho orchestration.
Event-driven architecture với Kafka.
- Nhân viên mới được training về policy trong 2 tuần onboarding đầu tiên.

## Infrastructure as Code
100% hạ tầng trên Terraform + Pulumi (cho complex logic).
GitOps workflow qua ArgoCD.
Infra monorepo với module system.

## Compute
EKS cluster: 3 node groups (general: m6i.2xlarge, compute: c6i.4xlarge, memory: r6i.2xlarge). Karpenter cho auto-scaling (thay Cluster Autoscaler). Spot instances cho non-critical workloads (tiết kiệm 60%). Fargate cho batch jobs.

## Database
PostgreSQL 16 trên Aurora Multi-AZ. Read replicas: 4 (2 cho application, 2 cho analytics). Backup continuous (PITR), retention 35 ngày. Global database cho cross-region DR. Instance: db.r6g.2xlarge. Connection pooling via PgBouncer.

## Storage
S3 cho objects, EFS cho shared storage.
Intelligent-Tiering tự động optimize cost.

## Networking
VPC per environment.
Transit Gateway kết nối VPCs.
PrivateLink cho AWS services.
Service mesh (Istio) cho inter-service communication.

## Container và orchestration
Kubernetes (EKS) cho mọi workload. Helm charts cho deployment. Kustomize cho environment-specific config. Pod Security Standards enforced. Resource requests/limits bắt buộc. Horizontal Pod Autoscaler cho mọi service.

## Backup và disaster recovery
RTO: 30 phút (failover sang GCP DR).
RPO: 5 phút (Aurora continuous backup + Kafka replication).
Cross-region replication real-time.

## Cost management
FinOps team (2 người) dedicated.
Kubecost cho Kubernetes cost allocation.
AWS Cost Explorer + custom Looker dashboard.

## Bảo trì hạ tầng
Zero-downtime maintenance. Rolling updates cho Kubernetes. RDS maintenance auto-applied trong maintenance window (Chủ nhật 3:00–5:00 AM). OS patching tự động qua Karpenter node rotation. Infra SLA: 99.99%.

