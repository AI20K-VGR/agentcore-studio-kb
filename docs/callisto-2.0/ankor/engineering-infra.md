# Quản lý hạ tầng — Ankor

## Kiến trúc tổng quan
Ankor chạy trên AWS (region ap-southeast-1). Kiến trúc monolith modular với 3 service chính: API Gateway, Core Service, và Worker Service. Database: PostgreSQL RDS. Cache: Redis ElastiCache.

## Infrastructure as Code
Toàn bộ hạ tầng quản lý bằng Terraform. Code Terraform lưu trên repo riêng (infra-ankor). Terraform state trên S3 + DynamoDB lock. Mọi thay đổi hạ tầng qua PR, review bởi DevOps team.

## Compute
EC2 instances cho application (m5.xlarge × 4 cho production). Auto Scaling Group với min 2, max 8 instances. Scale policy: CPU trên 70% trong 5 phút → scale up. Spot instances cho staging và dev.

## Database
PostgreSQL 15 trên RDS Multi-AZ. Read replicas: 2 cho production. Backup tự động hằng ngày, retention 30 ngày. Point-in-time recovery enabled. DB instance: db.r6g.xlarge. Max connections: 200.

## Storage
S3 cho file storage (user uploads, backups, logs). Lifecycle policy: Standard → IA sau 90 ngày → Glacier sau 365 ngày. Encryption at rest (SSE-S3). Versioning enabled cho bucket quan trọng.

## Networking
VPC với 3 AZ. Public subnet cho ALB, private subnet cho application, isolated subnet cho database. NAT Gateway cho outbound. Security Groups theo principle of least privilege. VPC Flow Logs enabled.

## Container và orchestration
Docker containers cho tất cả services. ECS Fargate cho production (serverless containers). ECR cho container registry. Task definition version control trên Terraform. Health check interval: 30 giây.

## Backup và disaster recovery
RTO (Recovery Time Objective): 4 giờ. RPO (Recovery Point Objective): 1 giờ. Cross-region backup sang ap-southeast-3 hằng ngày. DR drill mỗi 6 tháng. Runbook DR trên Confluence.

## Cost management
AWS budget alert khi chi phí đạt 80% và 100% ngân sách tháng. FinOps review hằng tháng. Reserved Instances cho workload ổn định (tiết kiệm 30%). Savings Plans cho compute. Monthly AWS cost: ~120 triệu VNĐ.

## Bảo trì hạ tầng
Maintenance window: Chủ nhật 2:00–6:00 AM. OS patching hằng tháng. RDS maintenance theo AWS schedule. Thông báo maintenance trước 1 tuần. Zero-downtime deployment cho application tier.
