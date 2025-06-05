
from hammerspace.client import HammerspaceApiClient 


HS_BASE_URL = "https://192.168.2.11:8443/mgmt/v1.2/rest"
HS_USERNAME = "admin"
HS_PASSWORD = "Password123!"
VERIFY_SSL = False
SHARE_NAME = "Share007"

client = HammerspaceApiClient(
            base_url=HS_BASE_URL,
            username=HS_USERNAME,
            password=HS_PASSWORD,
            verify_ssl=VERIFY_SSL
        )

## Create share Example
share_data = {
                "name": f"{SHARE_NAME}",
                "path": f"/{SHARE_NAME}", 
                "comment": "Share for the MI6 department's new campaign.",
                "exportOptions": [{"subnet": "192.168.2.0/23", "accessPermissions": "RW", "rootSquash": False, "insecure": False}],
            }

result = client.shares.create_share(
    share_data=share_data,
    monitor_task=True,
    task_timeout_seconds=600
)

print(result)
print("Final Status::",result.get('status',{}))

## Delete Share Example
# share_data = client.shares.get(spec=f"name=eq={SHARE_NAME}")

# result = client.shares.delete_share(share_data[0].get('uoid',{}).get('uuid', {}))

# print(result)

