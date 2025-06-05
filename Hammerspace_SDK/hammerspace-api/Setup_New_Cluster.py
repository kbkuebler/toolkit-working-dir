from hammerspace.client import HammerspaceApiClient 

SHARE_NAME = "Share007"

client = HammerspaceApiClient(
            base_url="https://192.168.2.10:8443/mgmt/v1.2/rest",
            username="admin",
            password="Password123!",
            verify_ssl=False
        )


#result = client.logical_volumes.get()
#result = client.licenses.get()
#result = client.ad.get()
#result = client.object_stores.get()
#result = client.backup.get()
#result = client.cntl.get()
#result = client.cntl.get_cluster_state()
result = client.cntl.accept_eula()
result = client.licenses.create_license(license_data={'activation_id':'b83e-ae9d-1813-441f-a94d-f43d-8c4b-e319'})
#result = client.cntl.shutdown_cluster()
#result = client.data_portals.get()
#result =  client.disk_drives.get()
#result = client.dnss.get()
#result = client.data_copy_to_object.list_object_storage_buckets()
#result = client.events.get()
#result = client.events.clear()
#result = client.events.get_summary()
#result = client.file_snapshots.create_file_snapshot(filenameexpression="Share007")

print(result)
#print("Final Status::",result.get('status',{}))

## Delete Share Example
# share_data = client.shares.get(spec=f"name=eq={SHARE_NAME}")

# result = client.shares.delete_share(share_data[0].get('uoid',{}).get('uuid', {}))

# print(result)

