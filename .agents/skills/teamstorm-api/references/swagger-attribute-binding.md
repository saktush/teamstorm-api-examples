# Attribute-binding diagnostic

1. Read the attribute and target workitem type.
2. Test the bodyless endpoint:

```http
POST /cwm/public/api/v1/workspaces/{workspace}/types/{type}/attributes/{attributeId}
```

3. Read both objects again. On the tested instance this call returned HTTP 500 for both type name and UUID.
4. A safer isolated workaround test is to create a new type with `attributeIds` already supplied.
5. Only after binding is visible, create a workitem containing the discriminated attribute value.
6. Verify through `GET .../workitems/{workitem}/attributes`, then test the update endpoint separately.

Interpret `AttributeNotFound`/404 during workitem creation in context: the definition may exist but be unavailable to that workitem type. Record status, redacted body, and post-operation read-back. Do not change an existing production type for diagnosis.
