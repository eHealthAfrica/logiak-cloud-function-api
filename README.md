# Logiak API

### Purpose

 Provide a consistent Web based API a single Logiak project in order to:
  - Authenticate users
  - Enforce Rules Based Access Control implemented in Logiak
  - Abstract the internal database structure of Logiak
  - Perform cost-effective queries

## Deployment Requirements:

 - FIREBASE_URL: url of the firebase project
 - WEB_API_KEY: web api-key for the firebase project, to allow proxying of authentication
 - LOGIAK_APP_ID: application_id of the targeted project in logiak

Optional [default]:
 - CORS_DOMAIN [\*]


## Services


### Auth `/auth`

Much like a password grant for a token, we expect user credentials to be POSTed to this endpoint. 

We expect a JSON payload of:
 ```json
{
    "username": "the username",
    "password": "the password"
}
```

On the back-end, we do the following.

 - Perform a firebase authentication of the user with the given credentials
 - Check to see if the user has an entry in`inits` for this project
 - If successful create a session object containing:
 ```python
{
    "{the_user_id}" : {
        "session_key": "{session_key}"
        "start_time": {epoch_start_time},
        "session_length": {length_of_validity_seconds}
 }
 ```
 - If successful, return the session object -> the caller as JSON.


ALL other operations require `Logiak-User-Id` and `Logiak-Session-Key` be included in `Headers`.

### Metadata Operations `/meta`

_*requires headers*_ `Logiak-Session-Key` && `Logiak-User-Id`




#### `/meta/app` [GET]

Current Metadata about the most current deployed App Version

References RTDB: {app_id}/settings

#### `/meta/app/{app_version}/{app_language}` [GET]

The Application definition of a version/language combination of the App.  Contains Tables / Etc. _Should be cached on the client side!_

References RTDB: apps/{app_alias}/{app_version}/settings/{language}/json

#### `/meta/schema/{app_version}` [GET]

A listing of schemas available for a particular App Version

References RTDB: objects/{app_id}/settings/{app_version(escaped)} -> List[schema_ids]

#### `/meta/schema/{app_version}/{schema_name}` [GET]

The Avro Schema for a version/object type combination. _Should be cached on the client side!_

References RTDB: objects/{app_id}/settings/{app_version(escaped)}/{schema_name} -> Schema




### Data Operations `/data`

_*requires headers*_ `Logiak-Session-Key` && `Logiak-User-Id`


#### `/data/{data_type}/query` [POST]
(See Query Language)[https://firebase.google.com/docs/firestore/reference/rest/v1/StructuredQuery]
 - supports `where`, `orderby`, `startAt`, `endAt`
 - pre-filters for allowed documents for user.

#### `/data/{data_type}/read/{document_id}` [GET]

 - Returns the requested document if available


#### `/data/{data_type}/create/{app_version}` [POST]

 - Adds values to system fields
 - Validates Data
 - Creates or Overwrites instance in database




## Example

Authenticate session.

```bash
curl -X POST \
    --header "Content-Type: application/json" \
    --data '{"username":"${USER_ID}","password":"password"}' \
    https://${SERVER}/auth
```

Save the returned session_key to use in subsequent calls. 


Get the current metadata for the app. Note the app version for subsequent calls.

```bash
curl -X GET \
    --header "logiak_user_id: ${USER_ID}" \
    --header "logiak_session_key: ${SESSION_KEY}" \
    https://${SERVER}/meta/app
```

Get other meta data about the current version of the app.


`/meta/app/{version}/{language} -> The App definition`

```bash
curl -X GET \
    --header "logiak_user_id: ${USER_ID}" \
    --header "logiak_session_key: ${SESSION_KEY}" \
    https://${SERVER}/meta/app/0.0.26/en
```


`/meta/schema/{version} -> List of available [Schema]`

```bash
curl -X GET \
    --header "logiak_user_id: ${USER_ID}" \
    --header "logiak_session_key: ${SESSION_KEY}" \
    https://${SERVER}/meta/schema/0.0.26
```


`/meta/schema/{version}/{type} -> A single Schema`

```bash
curl -X GET \
    --header "logiak_user_id: ${USER_ID}" \
    --header "logiak_session_key: ${SESSION_KEY}" \
    https://${SERVER}/meta/schema/0.0.26/batch
```



`Get Data by Type /data/{type}/query`

```bash
curl -X POST \
    --header "logiak_user_id: ${USER_ID}" \
    --header "logiak_session_key: ${SESSION_KEY}" \
    https://${SERVER}/data/batch/query
```bash