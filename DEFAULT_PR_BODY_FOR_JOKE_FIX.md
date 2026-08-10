## Summary

* correct the async joke test mock to match httpx.Response.json() behavior
* keep production code unchanged

## Validation

* GitHub Actions should run the existing validation workflow
* full pytest suite is expected to validate the change
