variable "aws_region" {
    description = "AWS region"
    type = string
    default = "ap-southeast-1"
}

variable "project_name" {
    description = "AWS s3 bucket"
    type = string
}

variable "redshift_username" {
    description = "AWS redshift username"
    type = string
} 

variable "redshift_password" {
    description = "AWS redshift password"
    type = string
} 