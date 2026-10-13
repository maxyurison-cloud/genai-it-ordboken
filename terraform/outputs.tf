output "app_url" {
  description = "Open this in a browser"
  value       = "http://${aws_instance.web.public_ip}"
}
