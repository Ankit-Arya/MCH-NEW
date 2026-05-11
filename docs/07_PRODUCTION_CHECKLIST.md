# Production Checklist

## Before Go-Live

- [ ] Final grading scale confirmed
- [ ] Video rule confirmed: maximum 15 sec or minimum 15 sec
- [ ] N/A approval rule confirmed
- [ ] SM late inspection rule confirmed
- [ ] Monthly bill value source confirmed
- [ ] Penalty approval authority confirmed
- [ ] User roles and line/station mappings confirmed
- [ ] SSL certificate installed
- [ ] Default passwords changed
- [ ] Backup and restore tested
- [ ] PostgreSQL storage path verified
- [ ] MinIO storage path verified
- [ ] Audit retention policy approved
- [ ] Load test completed
- [ ] Security review completed
- [ ] UAT signed off by Operations/HK Cell

## Daily Operational Checks

- [ ] API container running
- [ ] PostgreSQL container healthy
- [ ] MinIO accessible
- [ ] Redis running
- [ ] Worker running
- [ ] Scheduled backup completed
- [ ] No failed media processing queue

## Security Hardening

- [ ] Disable public MinIO bucket access
- [ ] Use strong JWT secret
- [ ] Enable HTTPS
- [ ] Restrict SSH access
- [ ] Restrict database port from public network
- [ ] Keep audit logs append-only
- [ ] Use non-default admin account
