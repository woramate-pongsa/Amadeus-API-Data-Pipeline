## Redshift Serverless
resource "aws_redshiftserverless_namespace" "redshift_namespace" {
    namespace_name      = "${var.project_name}-data-warehouse"
    db_name             = "main_db"
    admin_username      = var.redshift_username
    admin_user_password = var.redshift_password
    iam_roles           = [aws_iam_role.redshift_access_role.arn]
    tags = {
        Name = "${var.project_name}-redshift-namespace"
    }
}

resource "aws_redshiftserverless_workgroup" "redshift_workgroup" {
workgroup_name  = "${var.project_name}-workgroup"
namespace_name  = aws_redshiftserverless_namespace.redshift_namespace.namespace_name
subnet_ids      = [
    aws_subnet.private_subnet_1.id,
    aws_subnet.private_subnet_2.id,
    aws_subnet.private_subnet_3.id
]
security_group_ids = [aws_security_group.redshift_security_group.id]  
publicly_accessible = false # ปิดไม่ให้เข้าจากเน็ตโดยตรง (ปลอดภัยสุดๆ)
tags = { Name = "woramate-redshift-workgroup" }
}