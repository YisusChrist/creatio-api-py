![Creatio](https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/Creatio_logo.svg/2560px-Creatio_logo.svg.png)

This Python script is designed for testing the OData API of Creatio. It includes functionality for authentication, making generic HTTP requests to the OData service, and performing various operations on object collections.

Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
  - [Authentication](#authentication)
  - [Add a Record to a Collection](#add-a-record-to-a-collection)
  - [Modify a Record in a Collection](#modify-a-record-in-a-collection)
  - [Get Data from a Collection](#get-data-from-a-collection)
  - [Delete a Record from a Collection](#delete-a-record-from-a-collection)
  - [Handle information from the API session](#handle-information-from-the-api-session)
- [License](#license)

# Features

- **Authentication**: Authenticate and obtain a session cookie for subsequent requests.
- **HTTP Requests**: Make generic HTTP requests (GET, POST, PATCH, DELETE) to the OData service.
- **Collection Operations**: Interact with object collections, including adding, modifying, and deleting records.
- **Logging**: Enable debugging to log detailed information about HTTP requests and responses.

# Installation

`creatio-odata-api` can be installed easily as a PyPI package. Just run the following command:

```bash
pip3 install creatio-odata-api
```

> [!IMPORTANT]
> For best practices and to avoid potential conflicts with your global Python environment, it is strongly recommended to install this program within a virtual environment. Avoid using the --user option for global installations. We highly recommend using [pipx](https://pypi.org/project/pipx) for a safe and isolated installation experience. Therefore, the appropriate command to install `creatio-odata-api` would be:
>
> ```bash
> pipx install creatio-odata-api
> ```

# Usage

The package allows you to stablish connection to any Creatio environment using the credentials of a user with the necessary permissions. The following steps will guide you through the process of setting up the environment and running the script.

1. Set up your environment variables by creating a .env file with the following content:

   ```env
   CREATIO_USERNAME=your_username
   CREATIO_PASSWORD=your_password
   ```

2. Authenticate to the Creatio environment:

   ```python
   from creatio_odata_api.api import CreatioODataAPI
   from creatio_odata_api.utils import print_exception

   creatio_url: str = "https://your-environment.creatio.com"
   api = CreatioODataAPI(base_url=creatio_url)
   try:
      # Authenticate with the API
      api.authenticate()
   except Exception as e:
      print_exception(e, f"Unable to authenticate on {creatio_url}")
   ```

   If you don't want to use the .env file, you can pass the credentials directly to the `authenticate` method:

   ```python
   api.authenticate(username="your_username", password="your_password")
   ```

   The `authenticate` method will return an HTTP response object. If the status code is 200, the authentication was successful, and the session cookie is stored in the `api` object. Therefore, your don't need to pass the cookie to the other methods, it will be used automatically for the next requests.

   However, if you want to check the cookie value, you can access it using the `cookie` attribute:

   ```python
   cookie = api.session_cookies
   print(cookie)
   ```

   Response Cookie:

   ```python
   {
      'BPMLOADER': 'lima0ugkfcecqs23bdeio1k4',
      '.ASPXAUTH': '7AE0D4CDCD7DCB01A65ACAF85D8DAC0D842B41745CB17A4AEF4C6F18701757AEA7EAFA90565091E61A54E5559A2B1113C6A6EDA78EFEDECD10176937BBD7F9FEBCAC9210963D42AC059C9858A29F7C903E9CB5FAC3B36CF273B8FF94850CDC01D21F69874990586EEDE392900D87C9D09DF3053D7E5AEDB0D79E0F9172634C9F2566424A5B5F38BD58C2EF1BC06E98ED9168488F7ADE262147E73A3A082CB8CAC74C6A4F6B50555D1ED2A93FC05070E0607B79B32F4ED8B8306918E1F2CCAC1C88CB651DFDF795A36E0A03EFFE0A8AA960BDCD358065C8FDABBF9C59A3FC0B2FEFD77C7E1FC484B6CDAB162F2A5EFB0084FDAA6404AF2773C3DBB8147F83E7040400172E332523BB415AC9432269BF5ED53E2BD70C336CDA513228617AC7A2C9BAD79CBEFE1DE193B1C8E5D6EC836D9F67F4F4033F759CA7E7EDBC433C72441110ECCBD386E05E960822BE049D7BACE51EDFA6B47E57BC654C4B7B3D047AEF9F14F92ACAB37D4286FC9494656B489DE1512DB33869291366E70DA77C9BEDB67706F5896F65B3F835D3C6B4D3367FC7FD086556E1B6F7777FD123848A7038F0AF923758AE398705069FF295D4C0CC180710DC2DE26DD91C09025F0093784241B60757937FEE936A2B80995617DFBB7FE54262F85F7AD4D5465413554A1C67BB0FD21793826C050E8AB83D39747A049C138792E079',
      'BPMCSRF': 'ezBoM358i3BgxRyW1kKF0u',
      'UserType': 'General',
      'UserName': '83|117|112|101|114|118|105|115|111|114'
   }
   ```

# Examples

## Authentication

```python
from creatio_odata_api.api import CreatioODataAPI
from creatio_odata_api.utils import print_exception

creatio_url: str = "https://your-environment.creatio.com"
api = CreatioODataAPI(base_url=creatio_url)
try:
   # Authenticate with the API
   api.authenticate()
except Exception as e:  # pylint: disable=broad-except
   print_exception(e, f"Unable to authenticate on {creatio_url}")
```

## Add a Record to a Collection

```python
payload: dict[str, str] = {
   "UsrEmail": "test@test.com",
   "UsrTelefono": "123456789",
   "UsrDescripcionBienContratado": "Test",
   # ... other fields ...
}

response = api.add_collection_data("Case", data=payload)
```

- Response code: 201 Created
- Response body:

```python
{
   '@odata.context': 'https://your-environment.creatio.com/0/odata/$metadata#Case/$entity',
   'Id': 'cf8c6558-9e3e-48ca-a237-765b0f54b798',
   'CreatedOn': '2024-06-17T15:28:32.7013964Z',
   'CreatedById': '410006e1-ca4e-4502-a9ec-e54d922d2c00',
   'ModifiedOn': '2024-06-17T15:28:32.7013964Z',
   'ModifiedById': '410006e1-ca4e-4502-a9ec-e54d922d2c00',
   'ProcessListeners': 0,
   'Number': 'SR00005250',
   'UsrDescripcionBienContratado': 'Test',
   'UsrEmail': 'test@test.com',
   'UsrTelefono': '123456789',
   # ... other fields ...
}
```

Creatio returns the created record with the `Id` field. You can use this ID to modify or delete the record later.

## Modify a Record in a Collection

```python
payload: dict[str, str] = {
   "UsrDescripcionBienContratado": "New test description",
}

record_id = "cf8c6558-9e3e-48ca-a237-765b0f54b798"
response = api.modify_collection_data("Case", record_id=record_id, data=payload)
```

- Response code: 204 No Content
- Response body: None

The response code 204 indicates that the record has been successfully updated. Creatio does not return a body in this case.

## Get Data from a Collection

```python
record_id = "cf8c6558-9e3e-48ca-a237-765b0f54b798"
response = api.get_collection_data("Case", record_id=record_id)
```

- Response code: 200 OK
- Response body:

```python
{
   '@odata.context': 'https://your-environment.creatio.com/0/odata/$metadata#Case/$entity',
   'Id': 'cf8c6558-9e3e-48ca-a237-765b0f54b798',
   'CreatedOn': '2024-06-17T15:28:32.7013964Z',
   'CreatedById': '410006e1-ca4e-4502-a9ec-e54d922d2c00',
   'ModifiedOn': '2024-06-17T15:28:32.7013964Z',
   'ModifiedById': '410006e1-ca4e-4502-a9ec-e54d922d2c00',
   'ProcessListeners': 0,
   'Number': 'SR00005250',
   'UsrDescripcionBienContratado': 'New test description',
   'UsrEmail': 'test@test.com',
   'UsrTelefono': '123456789',
   # ... other fields ...
}
```

As you can see, the field `UsrDescripcionBienContratado` has been updated.

## Delete a Record from a Collection

- Response code: 204 No Content
- Response body: None

```python
record_id = "cf8c6558-9e3e-48ca-a237-765b0f54b798"
response = api.delete_collection_data("Case", record_id=record_id)
```

The response code 204 indicates that the record has been successfully deleted. Creatio does not return a body in this case.

If we try to get the record again, we will get a 404 Not Found response:

```python
record_id = "cf8c6558-9e3e-48ca-a237-765b0f54b798"
response = api.get_collection_data("Case", record_id=record_id)
```

- Response code: 404 Not Found
- Response body: None

## Handle information from the API session

It is possible to retrieve information like the total number of requests made, the base url used for the class instance, and the session cookies.

```python
total_requests = api.total_requests
# 6
base_url = api.base_url
# 'https://your-environment.creatio.com'
session_cookies = api.session_cookies
# {...}
```

Additionally, you can modify the object's base url if needed:

```python
api.base_url = "https://another-environment.creatio.com"
```

# License

This script is licensed under the [GNU General Public License v3.0](https://opensource.org/licenses/GPL-3.0).
