HOST_MAPPING = {
    "AutomationServer01": "aws-auto-core-01",
    "AwsAI-Backend Server": "aws-ai-svr-01",
    "AwsBastonServer": "aws-mgmt-baston-01",
    "Monitoring-EC2": "aws-mon-core-01",
    "AwsManagedServer01": "aws-managed-svr-01",
    "AwsSplunkServer": "aws-splunk-svr-01",
    "AwsVPNGateway": "aws-vpn-gw-01",
}


def resolve_host_identity(host: str) -> str:
    return HOST_MAPPING.get(host, host)
