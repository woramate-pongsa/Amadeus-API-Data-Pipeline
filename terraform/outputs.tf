output "server_public_id" {
    value = aws_instance.airflow_server.public_ip
}

output "redshift_endpoint" {
    value = aws_redshiftserverless_workgroup.redshift_workgroup.endpoint
}