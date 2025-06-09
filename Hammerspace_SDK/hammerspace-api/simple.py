from hammerspace.client import HammerspaceApiClient 

SHARE_NAME = "Share007"

client = HammerspaceApiClient(
            base_url="https://10.200.120.200:8443/mgmt/v1.2/rest",
            username="admin",
            password="1Hammerspace!",
            verify_ssl=False
        )
result = client.network_interfaces.get()


print("-" * 30)
print(result)
print("-" * 30)
