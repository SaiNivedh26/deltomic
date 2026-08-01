# Python SDK

## Setup & Initialization\#

1. Install Package:

```
pip install pingram-python
```

2. Import:

```
from pingram import Pingram, PingramRegion
```

3. Initialize and use as async context manager:

```
import asyncio

async def main():

    async with Pingram(api_key="pingram_sk_...") as client:

        # Use client methods here

        pass

asyncio.run(main())
```

| Name | Type | Description |
| --- | --- | --- |
| `api_key`\* | string | Your Pingram API key. You can get it from your [dashboard](https://app.pingram.io/environments) under Environments. |
| `region` | string | Optional. Region: `"us"` (default), `"eu"`, or `"ca"`. |
| `base_url` | string | Optional. Override the base URL directly. Use `https://api.ca.pingram.io` for the Canada region, and `https://api.eu.pingram.io` for the EU region. |

\\* required

Region specific example:

```
import asyncio

async def main():

    async with Pingram(api_key="pingram_sk_...", region="eu") as client:

        # Use client methods here

        pass

asyncio.run(main())
```

Or using base\_url directly:

```
import asyncio

async def main():

    async with Pingram(api_key="pingram_sk_...", base_url="https://api.eu.pingram.io") as client:

        # Use client methods here

        pass

asyncio.run(main())
```

## Send\#

### send()\#

Send a notification (email, SMS, etc.) to one user. Requires a notification `type` which categorizes this messages for future reporting, and channel-specific payloads such as `email` or `sms`. Recipient is specified with the `to` parameter. Returns a `trackingId` for error or delivery lookup through our Logs.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    sender_post_body = SenderPostBody()

    response = await client.send(sender_post_body)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **sender\_post\_body** | **SenderPostBody** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `type` | string | ID of the notification type (e.g. “welcome\_email”). Creates a new notification if it does not exist. |
| `to` | object | Recipient user. Provide `id`, `email`, or `number` to identify the user. |
| `to.id` | string | Unique user identifier. Required. |
| `to.email` | string | User’s email address for email notifications. |
| `to.number` | string | User’s phone number for SMS/call notifications. |
| `to.pushTokens` | object\[\] | Mobile push tokens (FCM, APN) for push notifications. |
| `to.pushTokens[].type` | “FCM” \| “APN” | (required) |
| `to.pushTokens[].token` | string | (required) |
| `to.pushTokens[].device` | object | (required) |
| `to.pushTokens[].device.app_id` | string |  |
| `to.pushTokens[].device.ad_id` | string |  |
| `to.pushTokens[].device.device_id` | string | (required) |
| `to.pushTokens[].device.platform` | string |  |
| `to.pushTokens[].device.manufacturer` | string |  |
| `to.pushTokens[].device.model` | string |  |
| `to.pushTokens[].environment` | string | used by APN to differentiate between sandbox and production builds (sandbox/undefined or production) |
| `to.webPushTokens` | object\[\] | Web push subscription config from the browser. |
| `to.webPushTokens[].sub` | object | (required) Configuration for a Push Subscription. This can be obtained on the frontend by calling serviceWorkerRegistration.pushManager.subscribe(). The expected format is the same output as JSON.stringify’ing a PushSubscription in the browser. |
| `to.webPushTokens[].sub.endpoint` | string | (required) |
| `to.webPushTokens[].sub.keys` | object | (required) |
| `to.webPushTokens[].sub.keys.p256dh` | string | (required) |
| `to.webPushTokens[].sub.keys.auth` | string | (required) |
| `to.timezone` | string | User’s timezone (e.g. “America/New\_York”) for scheduling. |
| `to.slackChannel` | string | The destination channel of slack notifications sent to this user. Can be either of the following: - Channel name, e.g. “test” - Channel name with # prefix, e.g. “#test” - Channel ID, e.g. “C1234567890” - User ID for DM, e.g. “U1234567890” - Username with @ prefix, e.g. “@test” |
| `to.slackToken` | object |  |
| `to.slackToken.access_token` | string |  |
| `to.slackToken.app_id` | string |  |
| `to.slackToken.authed_user` | object |  |
| `to.slackToken.authed_user.access_token` | string |  |
| `to.slackToken.authed_user.expires_in` | number |  |
| `to.slackToken.authed_user.id` | string |  |
| `to.slackToken.authed_user.refresh_token` | string |  |
| `to.slackToken.authed_user.scope` | string |  |
| `to.slackToken.authed_user.token_type` | string |  |
| `to.slackToken.bot_user_id` | string |  |
| `to.slackToken.enterprise` | object |  |
| `to.slackToken.enterprise.id` | string |  |
| `to.slackToken.enterprise.name` | string |  |
| `to.slackToken.error` | string |  |
| `to.slackToken.expires_in` | number |  |
| `to.slackToken.incoming_webhook` | object |  |
| `to.slackToken.incoming_webhook.channel` | string |  |
| `to.slackToken.incoming_webhook.channel_id` | string |  |
| `to.slackToken.incoming_webhook.configuration_url` | string |  |
| `to.slackToken.incoming_webhook.url` | string |  |
| `to.slackToken.is_enterprise_install` | boolean |  |
| `to.slackToken.needed` | string |  |
| `to.slackToken.ok` | boolean | (required) |
| `to.slackToken.provided` | string |  |
| `to.slackToken.refresh_token` | string |  |
| `to.slackToken.scope` | string |  |
| `to.slackToken.team` | object |  |
| `to.slackToken.team.id` | string |  |
| `to.slackToken.team.name` | string |  |
| `to.slackToken.token_type` | string |  |
| `to.slackToken.warning` | string |  |
| `to.slackToken.response_metadata` | object |  |
| `to.slackToken.response_metadata.warnings` | string\[\] |  |
| `to.slackToken.response_metadata.next_cursor` | string |  |
| `to.slackToken.response_metadata.scopes` | string\[\] |  |
| `to.slackToken.response_metadata.acceptedScopes` | string\[\] |  |
| `to.slackToken.response_metadata.retryAfter` | number |  |
| `to.slackToken.response_metadata.messages` | string\[\] |  |
| `to.lastSeenTime` | string | Last activity timestamp. Updated automatically. Read-only. |
| `to.updatedAt` | string | Last update timestamp. Read-only. |
| `to.createdAt` | string | Creation timestamp. Read-only. |
| `to.emailSuppressionStatus` | object | Bounce or complaint status if email was suppressed. Read-only. |
| `to.emailSuppressionStatus.reason` | “Bounce” \| “Complaint” | (required) |
| `to.emailSuppressionStatus.details` | object | (required) |
| `forceChannels` | (“EMAIL” \| “INAPP\_WEB” \| “SMS” \| “CALL” \| “VOICE” \| “PUSH” \| “WEB\_PUSH” \| “SLACK”)\[\] | Override which channels to send to (e.g. \[“EMAIL”, “SMS”\]). Bypasses notification channel config. |
| `parameters` | Record<string, any> | Key-value pairs for template merge tags. Replaces placeholders like {{firstName}} in templates. |
| `secondaryId` | string | Optional sub-notification identifier for grouping or tracking. |
| `templateId` | string | Specific template ID to use. If omitted, uses the default template for each channel. |
| `subNotificationId` | string | Sub-notification identifier (e.g. for grouping related notifications). |
| `options` | object | Per-channel overrides for send options (email, APN, FCM). |
| `options.email` | object | Email-specific overrides. |
| `options.email.replyToAddresses` | string\[\] | Reply-to addresses for the email. |
| `options.email.ccAddresses` | string\[\] | CC recipients. |
| `options.email.bccAddresses` | string\[\] | BCC recipients. |
| `options.email.fromAddress` | string | Override sender email address. |
| `options.email.fromName` | string | Override sender display name. |
| `options.email.attachments` | (object \| object)\[\] | File attachments (by URL or inline base64 content). Inline `content`: ~4 MB raw per file (413 if exceeded). URL `url`: up to 20 MB per file. |
| `options.email.condition` | string | Conditional expression for when to send (e.g. merge tag logic). |
| `options.apn` | object | Apple Push Notification (APN) overrides. |
| `options.apn.expiry` | number | Seconds until the notification expires. |
| `options.apn.priority` | number | Delivery priority (10 = immediate, 5 = power-saving). |
| `options.apn.collapseId` | string | Group notifications with the same ID (replaces previous). |
| `options.apn.threadId` | string | Thread identifier for grouping notifications. |
| `options.apn.badge` | number | Badge count on app icon. |
| `options.apn.sound` | string | Sound file name. |
| `options.apn.contentAvailable` | boolean | Silent background notification (no alert). |
| `options.fcm` | object | Firebase Cloud Messaging (FCM) overrides. |
| `options.fcm.android` | object | Android-specific FCM options. |
| `options.fcm.android.collapseKey` | string | Collapse key for grouping messages. |
| `options.fcm.android.priority` | “high” \| “normal” | Delivery priority. |
| `options.fcm.android.ttl` | number | Time to live in seconds. |
| `options.fcm.android.restrictedPackageName` | string | Restrict delivery to a specific package. |
| `options.push` | object | Cross-platform mobile push options (applied to both APN and FCM). |
| `options.push.customData` | Record<string, string> | Up to 3 custom string key-value pairs for deep linking. Included in both APN and FCM payloads. |
| `schedule` | string |  |
| `email` | object | Inline email content (subject, html). Use when not using templates. |
| `email.subject` | string | (required) Email subject line. |
| `email.html` | string | (required) HTML body content. |
| `email.previewText` | string | Preview/snippet text shown in inbox. |
| `email.senderName` | string | Display name of sender. |
| `email.senderEmail` | string | Sender email address. |
| `inapp` | object | Inline in-app content (title, url, image). |
| `inapp.title` | string | (required) Notification title. |
| `inapp.url` | string | URL to open when clicked. |
| `inapp.image` | string | Image URL. |
| `sms` | object | Inline SMS content (message, autoReply, from, mediaUrls). |
| `sms.message` | string | SMS/MMS body text. |
| `sms.mediaUrls` | string\[\] | Public HTTPS URLs of media to attach (MMS). Carriers fetch these via GET. Total size limits apply per provider. |
| `sms.autoReply` | object |  |
| `sms.autoReply.message` | string | (required) Auto-reply message to send when user texts in. |
| `sms.from` | string | Override the sender phone number. Must be a verified number on your account. |
| `call` | object | Inline call content (message). |
| `call.message` | string | (required) Text to speak (TTS). |
| `web_push` | object | Inline web push content (title, message, icon, url). |
| `web_push.title` | string | (required) Notification title. |
| `web_push.message` | string | (required) Body text. |
| `web_push.icon` | string | Icon URL. |
| `web_push.url` | string | URL to open when clicked. |
| `mobile_push` | object | Inline mobile push content (title, message). |
| `mobile_push.title` | string | (required) Notification title. |
| `mobile_push.message` | string | (required) Body text. |
| `slack` | object | Inline Slack content (text, blocks, etc.). |
| `slack.text` | string | (required) Fallback plain text (required when using blocks). |
| `slack.blocks` | Record<string, any>\[\] | Slack Block Kit blocks. |
| `slack.username` | string | Override bot username. |
| `slack.icon` | string | Icon: emoji (e.g. “:smile:”) or URL. Default: bot’s icon. |
| `slack.thread_ts` | string | Parent message `ts` to post in a thread. |
| `slack.reply_broadcast` | boolean | When true with thread\_ts, broadcasts reply to channel. Default: false. |
| `slack.parse` | “full” \| “none” | URL parsing: “full” (clickable links) or “none”. Default: “none”. |
| `slack.link_names` | boolean | Convert channel and username refs to Slack links. Default: false. |
| `slack.mrkdwn` | boolean | Enable Slack markup ( _bold_, _italic_, `code`). Default: true. |
| `slack.unfurl_links` | boolean | Unfurl link previews. Default: true. |
| `slack.unfurl_media` | boolean | Unfurl media previews. Default: true. |
| `slack.metadata` | object | Slack message metadata with optional work object entities. Combines standard Slack message metadata fields with an array of entity objects. |
| `slack.metadata.entities` | object\[\] | An array of work object entities. |
| `slack.metadata.entities[].entity_type` | string | (required) Entity type (e.g., ‘slack#/entities/task’, ‘slack#/entities/file’). |
| `slack.metadata.entities[].entity_payload` | Record<string, any> | (required) Schema for the given entity type. |
| `slack.metadata.entities[].external_ref` | object | (required) Reference used to identify an entity within the developer’s system. |
| `slack.metadata.entities[].external_ref.id` | string | (required) |
| `slack.metadata.entities[].external_ref.type` | string |  |
| `slack.metadata.entities[].url` | string | (required) URL used to identify an entity within the developer’s system. |
| `slack.metadata.entities[].app_unfurl_url` | string | The exact URL posted in the source message. Required in metadata passed to `chat.unfurl`. |
| `slack.metadata.event_type` | string | A human readable alphanumeric string representing your application’s metadata event. |
| `slack.metadata.event_payload` | Record<string, any> | A free-form object containing whatever data your application wishes to attach to messages. |

## Webhooks\#

### webhooks\_delete\_events\_webhook()\#

Delete the events webhook configuration for the current account/environment.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.webhooks.webhooks_delete_events_webhook()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### webhooks\_get\_events\_webhook()\#

Get the events webhook configuration for the current account/environment.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.webhooks.webhooks_get_events_webhook()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### webhooks\_upsert\_events\_webhook()\#

Create or update the events webhook configuration for the current account/environment.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    events_webhook_upsert_request = EventsWebhookUpsertRequest()

    response = await client.webhooks.webhooks_upsert_events_webhook(events_webhook_upsert_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **events\_webhook\_upsert\_request** | **EventsWebhookUpsertRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `webhook` | string | (required) Destination URL that receives webhook event payloads. Must be a valid http(s) URL. |
| `events` | (“EMAIL\_OPEN” \| “EMAIL\_CLICK” \| “EMAIL\_FAILED” \| “EMAIL\_DELIVERED” \| “EMAIL\_UNSUBSCRIBE” \| “EMAIL\_INBOUND” \| “INAPP\_WEB\_FAILED” \| “INAPP\_WEB\_UNSUBSCRIBE” \| “SMS\_DELIVERED” \| “SMS\_FAILED” \| “SMS\_UNSUBSCRIBE” \| “SMS\_SUBSCRIBE” \| “SMS\_INBOUND” \| “PUSH\_FAILED” \| “PUSH\_UNSUBSCRIBE” \| “CALL\_FAILED” \| “CALL\_UNSUBSCRIBE” \| “WEB\_PUSH\_FAILED” \| “WEB\_PUSH\_UNSUBSCRIBE” \| “SLACK\_FAILED” \| “SLACK\_UNSUBSCRIBE”)\[\] | (required) List of event types that should be forwarded to the webhook URL. |

## Addresses\#

### addresses\_create\_address()\#

Create a new email inbox. Omit `domain` for a built-in `@mail.pingram.io` address; set `domain` and `displayName` for a custom address on a verified domain.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    create_address_request = CreateAddressRequest()

    response = await client.addresses.addresses_create_address(create_address_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **create\_address\_request** | **CreateAddressRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `prefix` | string | (required) |
| `domain` | string |  |
| `displayName` | string |  |

### addresses\_delete\_address()\#

Delete a custom inbound address. Builtin addresses cannot be deleted.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    full_address = 'full_address_example'

    response = await client.addresses.addresses_delete_address(full_address)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **full\_address** | **str** | Full address to delete (e.g. [hello@example.com](mailto:hello@example.com)) |  |

### addresses\_list\_addresses()\#

List email inboxes (addresses) configured for receiving. Custom addresses must use a verified domain.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.addresses.addresses_list_addresses()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### addresses\_update\_address()\#

Update an inbox prefix or display name.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    update_address_request = UpdateAddressRequest()

    response = await client.addresses.addresses_update_address(update_address_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **update\_address\_request** | **UpdateAddressRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `fullAddress` | string | (required) |
| `prefix` | string |  |
| `displayName` | string |  |

## Domains\#

### domains\_add\_domain()\#

Add and start verification for a new sender domain. Pass the domain only (not a full email address).

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    post_senders_request_body = PostSendersRequestBody()

    response = await client.domains.domains_add_domain(post_senders_request_body)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **post\_senders\_request\_body** | **PostSendersRequestBody** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `sender` | string | (required) |

### domains\_delete\_domain()\#

Remove a sender domain from the account.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    sender = 'sender_example'

    response = await client.domains.domains_delete_domain(sender)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **sender** | **str** | Sender domain (URL encoded) |  |

### domains\_list\_domains()\#

List sender domains configured for the account (for outbound email).

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.domains.domains_list_domains()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### domains\_start\_domain\_verification()\#

Start SES domain verification (DNS readiness is checked client-side via checkDomainDns)

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    sender = 'sender_example'

    response = await client.domains.domains_start_domain_verification(sender)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **sender** | **str** | Sender domain (URL encoded) |  |

## Email\#

### email\_send()\#

Send an email. Requires `type`, `to`, `subject`, and `html`. Optional: `fromAddress`, `fromName`, `schedule`, attachments. The fromAddress must be a verified domain; otherwise our built-in address will be used which is fine for testing purposes.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    send_email_request = SendEmailRequest()

    response = await client.email.email_send(send_email_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **send\_email\_request** | **SendEmailRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `type` | string | (required) The notification type to send. |
| `to` | string | (required) The email address of the recipient. |
| `subject` | string | (required) The subject of the email. |
| `html` | string | (required) The HTML body of the email. |
| `fromName` | string | The display name of the sender. |
| `fromAddress` | string | The email address of the sender. |
| `previewText` | string | The preview text of the email. |
| `replyToAddresses` | string\[\] | The reply-to addresses of the email. |
| `ccAddresses` | string\[\] | The CC addresses of the email. |
| `bccAddresses` | string\[\] | The BCC addresses of the email. |
| `attachments` | object\[\] | URL-based file attachments. Up to 20 MB per file. |
| `attachments[].filename` | string | (required) |
| `attachments[].url` | string | (required) |
| `schedule` | string | The ISO 8601 datetime to schedule the email. |

## Environments\#

### environments\_create\_environment()\#

Create a new environment for the account

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    environment_create_request = EnvironmentCreateRequest()

    response = await client.environments.environments_create_environment(environment_create_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **environment\_create\_request** | **EnvironmentCreateRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `title` | string | (required) |

### environments\_list\_environments()\#

Get all environments for the authenticated account

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.environments.environments_list_environments()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### environments\_update\_environment()\#

Update environment settings (title, secret, disable sending, secure mode)

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    client_id = 'client_id_example'

    environment_patch_request = EnvironmentPatchRequest()

    response = await client.environments.environments_update_environment(client_id, environment_patch_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **client\_id** | **str** | Environment client ID |  |
| **environment\_patch\_request** | **EnvironmentPatchRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `resetSecret` | boolean |  |
| `disableSending` | (“EMAIL” \| “INAPP\_WEB” \| “SMS” \| “CALL” \| “VOICE” \| “PUSH” \| “WEB\_PUSH” \| “SLACK”)\[\] |  |
| `title` | string |  |
| `secureMode` | boolean |  |

## Logs\#

### logs\_get\_log\_retention()\#

Get log retention period in days for the account

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.logs.logs_get_log_retention()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### logs\_get\_logs()\#

List recent notification logs for the authenticated account, newest first.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    limit = 3.4

    cursor = 'cursor_example'

    response = await client.logs.logs_get_logs(limit=limit, cursor=cursor)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **limit** | **float** | Maximum number of logs to return (default | \[optional\] |
| **cursor** | **str** | Pagination cursor for next page | \[optional\] |

### logs\_get\_logs\_by\_tracking\_ids()\#

Get logs by tracking IDs (comma-separated, max 25 IDs). Use after sending email or SMS to look up delivery status.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    tracking_ids = 'tracking_ids_example'

    response = await client.logs.logs_get_logs_by_tracking_ids(tracking_ids)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **tracking\_ids** | **str** | Comma-separated tracking IDs (URL encoded) |  |

### logs\_get\_logs\_query\_result()\#

Get results from a log query started with Start Log Query. Poll until status is Complete.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    query_id = 'query_id_example'

    response = await client.logs.logs_get_logs_query_result(query_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **query\_id** | **str** | Query ID returned by Start Log Query |  |

### logs\_start\_logs\_query()\#

Start an asynchronous log search over a date range. Returns a `queryId`; poll with Get Log Query Results until status is Complete.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    log_query_post_body = LogQueryPostBody()

    response = await client.logs.logs_start_logs_query(log_query_post_body)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **log\_query\_post\_body** | **LogQueryPostBody** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `dateRangeFilter` | number\[\] | A tuple of \[startTime, endTime\] for the date range filter, each representing a unix timestamp. |
| `userFilter` | string |  |
| `envIdFilter` | string\[\] |  |
| `statusFilter` | string |  |
| `channelFilter` | (“email” \| “inapp” \| “sms” \| “call” \| “voice” \| “web\_push” \| “mobile\_push” \| “slack”)\[\] |  |
| `notificationFilter` | string\[\] |  |

### logs\_tail\_logs()\#

Get last 100 logs from the stream

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.logs.logs_tail_logs()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

## Numbers\#

### numbers\_list()\#

List active phone numbers registered for the account, including voice agent binding state.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.numbers.numbers_list()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### numbers\_list\_released()\#

List released phone numbers. Released numbers may be purchased again with 2 weeks of being released. Released numbers may be removed from released list after 2 weeks.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.numbers.numbers_list_released()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### numbers\_order\_number()\#

Purchase a phone number for the authenticated account, or reactivate a released number owned by the account (preserves original createdAt). Pass `phoneNumber` in E.164 format (e.g. +15551234567).

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    order_phone_number_request = OrderPhoneNumberRequest()

    response = await client.numbers.numbers_order_number(order_phone_number_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **order\_phone\_number\_request** | **OrderPhoneNumberRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `phoneNumber` | string | (required) E.164 from search results |

### numbers\_release\_number()\#

Release a phone number from the account. No refund for the current billing month.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    phone_number = 'phone_number_example'

    response = await client.numbers.numbers_release_number(phone_number)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **phone\_number** | **str** | E.164 phone number to release |  |

### numbers\_search\_available()\#

Search for available phone numbers to purchase. Requires `countryCode` (e.g. US, CA). Use before ordering a number.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    country_code = 'country_code_example'

    features = 'features_example'

    area_code = 'area_code_example'

    limit = 3.4

    response = await client.numbers.numbers_search_available(country_code, features=features, area_code=area_code, limit=limit)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **country\_code** | **str** | ISO 3166-1 alpha-2 country code (e.g., US, CA) |  |
| **features** | **str** | Comma-separated | \[optional\] |
| **area\_code** | **str** | National destination / area code filter | \[optional\] |
| **limit** | **float** | Max results (default 10, max 50) | \[optional\] |

## Organization\#

### organization\_create()\#

Create organization after SMS verification bypass

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    create_organization_request = CreateOrganizationRequest()

    response = await client.organization.organization_create(create_organization_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **create\_organization\_request** | **CreateOrganizationRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `attribution` | Record<string, string> | First-touch PostHog props from the client; attached to signup events. |

### organization\_get\_usage()\#

Get usage for the authenticated account’s organization (new billing model).

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.organization.organization_get_usage()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### organization\_get\_usage\_history()\#

Get historical usage for the authenticated account’s organization over a date range.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    start_date = 'start_date_example'

    end_date = 'end_date_example'

    response = await client.organization.organization_get_usage_history(start_date, end_date)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **start\_date** | **str** | Start date (YYYY-MM-DD) for the range |  |
| **end\_date** | **str** | End date (YYYY-MM-DD) for the range |  |

## Profile\#

### profile\_accept\_invite()\#

Accept a team invitation using a token

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    accept_invite_request = AcceptInviteRequest()

    response = await client.profile.profile_accept_invite(accept_invite_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **accept\_invite\_request** | **AcceptInviteRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `token` | string | (required) |

### profile\_change\_email()\#

Change the email address of the authenticated user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    change_email_request = ChangeEmailRequest()

    response = await client.profile.profile_change_email(change_email_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **change\_email\_request** | **ChangeEmailRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `newEmail` | string | (required) |

### profile\_delete\_account()\#

Permanently delete the authenticated user’s account

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    delete_account_request = DeleteAccountRequest()

    response = await client.profile.profile_delete_account(delete_account_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **delete\_account\_request** | **DeleteAccountRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `reason` | string |  |

### profile\_disable\_mfa()\#

Disable MFA for the authenticated user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    type = 'type_example'

    response = await client.profile.profile_disable_mfa(type)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **type** | **str** | MFA type (e.g. SOFTWARE\_TOKEN\_MFA) |  |

### profile\_get\_mfa\_status()\#

Get MFA status for the authenticated user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.profile.profile_get_mfa_status()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### profile\_setup\_mfa()\#

Start TOTP MFA setup and return QR code data

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    mfa_setup_request = MFASetupRequest()

    response = await client.profile.profile_setup_mfa(mfa_setup_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **mfa\_setup\_request** | **MFASetupRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `type` | “SOFTWARE\_TOKEN\_MFA” | (required) MFA methods supported by the profile MFA API. |

### profile\_verify\_mfa()\#

Verify TOTP code and enable MFA

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    mfa_verify_request = MFAVerifyRequest()

    response = await client.profile.profile_verify_mfa(mfa_verify_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **mfa\_verify\_request** | **MFAVerifyRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `type` | “SOFTWARE\_TOKEN\_MFA” | (required) MFA methods supported by the profile MFA API. |
| `code` | string | (required) |
| `session` | string | (required) |

## PushSettings\#

### push\_settings\_delete\_push\_apn\_settings()\#

Delete Apple Push Notification (APN) configuration for the current account.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.push_settings.push_settings_delete_push_apn_settings()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### push\_settings\_delete\_push\_fcm\_settings()\#

Delete Firebase Cloud Messaging (FCM) configuration for the current account.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.push_settings.push_settings_delete_push_fcm_settings()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### push\_settings\_get\_push\_apn\_settings()\#

Get Apple Push Notification (APN) configuration for the current account.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.push_settings.push_settings_get_push_apn_settings()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### push\_settings\_get\_push\_fcm\_settings()\#

Get Firebase Cloud Messaging (FCM) configuration for the current account.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.push_settings.push_settings_get_push_fcm_settings()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### push\_settings\_upsert\_push\_apn\_settings()\#

Create or update Apple Push Notification (APN) configuration for the current account.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    apn_config = APNConfig()

    response = await client.push_settings.push_settings_upsert_push_apn_settings(apn_config)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **apn\_config** | **APNConfig** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `KeyId` | string | (required) |
| `Key` | string | (required) |
| `TeamId` | string | (required) |
| `Topic` | string | (required) |

### push\_settings\_upsert\_push\_fcm\_settings()\#

Create or update Firebase Cloud Messaging (FCM) configuration for the current account.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    push_settings_fcm_put_request = PushSettingsFCMPutRequest()

    response = await client.push_settings.push_settings_upsert_push_fcm_settings(push_settings_fcm_put_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **push\_settings\_fcm\_put\_request** | **PushSettingsFCMPutRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `fcmConfig` | string | (required) |

## Sender\#

### sender\_delete\_schedule()\#

Delete (unschedule) an already scheduled notification

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    tracking_id = 'tracking_id_example'

    response = await client.sender.sender_delete_schedule(tracking_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **tracking\_id** | **str** | The tracking ID of the scheduled notification |  |

### sender\_test\_email()\#

Test the emailer with a sample email

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    post_email_test_request = PostEmailTestRequest()

    response = await client.sender.sender_test_email(post_email_test_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **post\_email\_test\_request** | **PostEmailTestRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `notificationId` | string | (required) |
| `to` | string | (required) |
| `subject` | string | (required) |
| `html` | string | (required) |
| `fromAddress` | string | (required) |
| `fromName` | string | (required) |
| `previewText` | string |  |

### sender\_update\_schedule()\#

Update the body or schedule of an already scheduled notification.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    tracking_id = 'tracking_id_example'

    sender_post_body = SenderPostBody()

    response = await client.sender.sender_update_schedule(tracking_id, sender_post_body)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **tracking\_id** | **str** | The tracking ID of the scheduled notification |  |
| **sender\_post\_body** | **SenderPostBody** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `type` | string | ID of the notification type (e.g. “welcome\_email”). Creates a new notification if it does not exist. |
| `to` | object | Recipient user. Provide `id`, `email`, or `number` to identify the user. |
| `to.id` | string | Unique user identifier. Required. |
| `to.email` | string | User’s email address for email notifications. |
| `to.number` | string | User’s phone number for SMS/call notifications. |
| `to.pushTokens` | object\[\] | Mobile push tokens (FCM, APN) for push notifications. |
| `to.pushTokens[].type` | “FCM” \| “APN” | (required) |
| `to.pushTokens[].token` | string | (required) |
| `to.pushTokens[].device` | object | (required) |
| `to.pushTokens[].device.app_id` | string |  |
| `to.pushTokens[].device.ad_id` | string |  |
| `to.pushTokens[].device.device_id` | string | (required) |
| `to.pushTokens[].device.platform` | string |  |
| `to.pushTokens[].device.manufacturer` | string |  |
| `to.pushTokens[].device.model` | string |  |
| `to.pushTokens[].environment` | string | used by APN to differentiate between sandbox and production builds (sandbox/undefined or production) |
| `to.webPushTokens` | object\[\] | Web push subscription config from the browser. |
| `to.webPushTokens[].sub` | object | (required) Configuration for a Push Subscription. This can be obtained on the frontend by calling serviceWorkerRegistration.pushManager.subscribe(). The expected format is the same output as JSON.stringify’ing a PushSubscription in the browser. |
| `to.webPushTokens[].sub.endpoint` | string | (required) |
| `to.webPushTokens[].sub.keys` | object | (required) |
| `to.webPushTokens[].sub.keys.p256dh` | string | (required) |
| `to.webPushTokens[].sub.keys.auth` | string | (required) |
| `to.timezone` | string | User’s timezone (e.g. “America/New\_York”) for scheduling. |
| `to.slackChannel` | string | The destination channel of slack notifications sent to this user. Can be either of the following: - Channel name, e.g. “test” - Channel name with # prefix, e.g. “#test” - Channel ID, e.g. “C1234567890” - User ID for DM, e.g. “U1234567890” - Username with @ prefix, e.g. “@test” |
| `to.slackToken` | object |  |
| `to.slackToken.access_token` | string |  |
| `to.slackToken.app_id` | string |  |
| `to.slackToken.authed_user` | object |  |
| `to.slackToken.authed_user.access_token` | string |  |
| `to.slackToken.authed_user.expires_in` | number |  |
| `to.slackToken.authed_user.id` | string |  |
| `to.slackToken.authed_user.refresh_token` | string |  |
| `to.slackToken.authed_user.scope` | string |  |
| `to.slackToken.authed_user.token_type` | string |  |
| `to.slackToken.bot_user_id` | string |  |
| `to.slackToken.enterprise` | object |  |
| `to.slackToken.enterprise.id` | string |  |
| `to.slackToken.enterprise.name` | string |  |
| `to.slackToken.error` | string |  |
| `to.slackToken.expires_in` | number |  |
| `to.slackToken.incoming_webhook` | object |  |
| `to.slackToken.incoming_webhook.channel` | string |  |
| `to.slackToken.incoming_webhook.channel_id` | string |  |
| `to.slackToken.incoming_webhook.configuration_url` | string |  |
| `to.slackToken.incoming_webhook.url` | string |  |
| `to.slackToken.is_enterprise_install` | boolean |  |
| `to.slackToken.needed` | string |  |
| `to.slackToken.ok` | boolean | (required) |
| `to.slackToken.provided` | string |  |
| `to.slackToken.refresh_token` | string |  |
| `to.slackToken.scope` | string |  |
| `to.slackToken.team` | object |  |
| `to.slackToken.team.id` | string |  |
| `to.slackToken.team.name` | string |  |
| `to.slackToken.token_type` | string |  |
| `to.slackToken.warning` | string |  |
| `to.slackToken.response_metadata` | object |  |
| `to.slackToken.response_metadata.warnings` | string\[\] |  |
| `to.slackToken.response_metadata.next_cursor` | string |  |
| `to.slackToken.response_metadata.scopes` | string\[\] |  |
| `to.slackToken.response_metadata.acceptedScopes` | string\[\] |  |
| `to.slackToken.response_metadata.retryAfter` | number |  |
| `to.slackToken.response_metadata.messages` | string\[\] |  |
| `to.lastSeenTime` | string | Last activity timestamp. Updated automatically. Read-only. |
| `to.updatedAt` | string | Last update timestamp. Read-only. |
| `to.createdAt` | string | Creation timestamp. Read-only. |
| `to.emailSuppressionStatus` | object | Bounce or complaint status if email was suppressed. Read-only. |
| `to.emailSuppressionStatus.reason` | “Bounce” \| “Complaint” | (required) |
| `to.emailSuppressionStatus.details` | object | (required) |
| `forceChannels` | (“EMAIL” \| “INAPP\_WEB” \| “SMS” \| “CALL” \| “VOICE” \| “PUSH” \| “WEB\_PUSH” \| “SLACK”)\[\] | Override which channels to send to (e.g. \[“EMAIL”, “SMS”\]). Bypasses notification channel config. |
| `parameters` | Record<string, any> | Key-value pairs for template merge tags. Replaces placeholders like {{firstName}} in templates. |
| `secondaryId` | string | Optional sub-notification identifier for grouping or tracking. |
| `templateId` | string | Specific template ID to use. If omitted, uses the default template for each channel. |
| `subNotificationId` | string | Sub-notification identifier (e.g. for grouping related notifications). |
| `options` | object | Per-channel overrides for send options (email, APN, FCM). |
| `options.email` | object | Email-specific overrides. |
| `options.email.replyToAddresses` | string\[\] | Reply-to addresses for the email. |
| `options.email.ccAddresses` | string\[\] | CC recipients. |
| `options.email.bccAddresses` | string\[\] | BCC recipients. |
| `options.email.fromAddress` | string | Override sender email address. |
| `options.email.fromName` | string | Override sender display name. |
| `options.email.attachments` | (object \| object)\[\] | File attachments (by URL or inline base64 content). Inline `content`: ~4 MB raw per file (413 if exceeded). URL `url`: up to 20 MB per file. |
| `options.email.condition` | string | Conditional expression for when to send (e.g. merge tag logic). |
| `options.apn` | object | Apple Push Notification (APN) overrides. |
| `options.apn.expiry` | number | Seconds until the notification expires. |
| `options.apn.priority` | number | Delivery priority (10 = immediate, 5 = power-saving). |
| `options.apn.collapseId` | string | Group notifications with the same ID (replaces previous). |
| `options.apn.threadId` | string | Thread identifier for grouping notifications. |
| `options.apn.badge` | number | Badge count on app icon. |
| `options.apn.sound` | string | Sound file name. |
| `options.apn.contentAvailable` | boolean | Silent background notification (no alert). |
| `options.fcm` | object | Firebase Cloud Messaging (FCM) overrides. |
| `options.fcm.android` | object | Android-specific FCM options. |
| `options.fcm.android.collapseKey` | string | Collapse key for grouping messages. |
| `options.fcm.android.priority` | “high” \| “normal” | Delivery priority. |
| `options.fcm.android.ttl` | number | Time to live in seconds. |
| `options.fcm.android.restrictedPackageName` | string | Restrict delivery to a specific package. |
| `options.push` | object | Cross-platform mobile push options (applied to both APN and FCM). |
| `options.push.customData` | Record<string, string> | Up to 3 custom string key-value pairs for deep linking. Included in both APN and FCM payloads. |
| `schedule` | string |  |
| `email` | object | Inline email content (subject, html). Use when not using templates. |
| `email.subject` | string | (required) Email subject line. |
| `email.html` | string | (required) HTML body content. |
| `email.previewText` | string | Preview/snippet text shown in inbox. |
| `email.senderName` | string | Display name of sender. |
| `email.senderEmail` | string | Sender email address. |
| `inapp` | object | Inline in-app content (title, url, image). |
| `inapp.title` | string | (required) Notification title. |
| `inapp.url` | string | URL to open when clicked. |
| `inapp.image` | string | Image URL. |
| `sms` | object | Inline SMS content (message, autoReply, from, mediaUrls). |
| `sms.message` | string | SMS/MMS body text. |
| `sms.mediaUrls` | string\[\] | Public HTTPS URLs of media to attach (MMS). Carriers fetch these via GET. Total size limits apply per provider. |
| `sms.autoReply` | object |  |
| `sms.autoReply.message` | string | (required) Auto-reply message to send when user texts in. |
| `sms.from` | string | Override the sender phone number. Must be a verified number on your account. |
| `call` | object | Inline call content (message). |
| `call.message` | string | (required) Text to speak (TTS). |
| `web_push` | object | Inline web push content (title, message, icon, url). |
| `web_push.title` | string | (required) Notification title. |
| `web_push.message` | string | (required) Body text. |
| `web_push.icon` | string | Icon URL. |
| `web_push.url` | string | URL to open when clicked. |
| `mobile_push` | object | Inline mobile push content (title, message). |
| `mobile_push.title` | string | (required) Notification title. |
| `mobile_push.message` | string | (required) Body text. |
| `slack` | object | Inline Slack content (text, blocks, etc.). |
| `slack.text` | string | (required) Fallback plain text (required when using blocks). |
| `slack.blocks` | Record<string, any>\[\] | Slack Block Kit blocks. |
| `slack.username` | string | Override bot username. |
| `slack.icon` | string | Icon: emoji (e.g. “:smile:”) or URL. Default: bot’s icon. |
| `slack.thread_ts` | string | Parent message `ts` to post in a thread. |
| `slack.reply_broadcast` | boolean | When true with thread\_ts, broadcasts reply to channel. Default: false. |
| `slack.parse` | “full” \| “none” | URL parsing: “full” (clickable links) or “none”. Default: “none”. |
| `slack.link_names` | boolean | Convert channel and username refs to Slack links. Default: false. |
| `slack.mrkdwn` | boolean | Enable Slack markup ( _bold_, _italic_, `code`). Default: true. |
| `slack.unfurl_links` | boolean | Unfurl link previews. Default: true. |
| `slack.unfurl_media` | boolean | Unfurl media previews. Default: true. |
| `slack.metadata` | object | Slack message metadata with optional work object entities. Combines standard Slack message metadata fields with an array of entity objects. |
| `slack.metadata.entities` | object\[\] | An array of work object entities. |
| `slack.metadata.entities[].entity_type` | string | (required) Entity type (e.g., ‘slack#/entities/task’, ‘slack#/entities/file’). |
| `slack.metadata.entities[].entity_payload` | Record<string, any> | (required) Schema for the given entity type. |
| `slack.metadata.entities[].external_ref` | object | (required) Reference used to identify an entity within the developer’s system. |
| `slack.metadata.entities[].external_ref.id` | string | (required) |
| `slack.metadata.entities[].external_ref.type` | string |  |
| `slack.metadata.entities[].url` | string | (required) URL used to identify an entity within the developer’s system. |
| `slack.metadata.entities[].app_unfurl_url` | string | The exact URL posted in the source message. Required in metadata passed to `chat.unfurl`. |
| `slack.metadata.event_type` | string | A human readable alphanumeric string representing your application’s metadata event. |
| `slack.metadata.event_payload` | Record<string, any> | A free-form object containing whatever data your application wishes to attach to messages. |

## Sms\#

### sms\_send()\#

Send an SMS or MMS directly without a template. Requires `type` and `to`. Pass `message` and/or `mediaUrls`. Optional: `from`, `schedule`.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    send_sms_request = SendSmsRequest()

    response = await client.sms.sms_send(send_sms_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **send\_sms\_request** | **SendSmsRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `type` | string | (required) The notification type to send. |
| `to` | string | (required) The phone number of the recipient. |
| `message` | string | The message of the SMS or MMS notification. Optional when `mediaUrls` is provided. |
| `mediaUrls` | string\[\] | Public HTTPS URLs of media to attach (MMS). |
| `schedule` | string | The ISO 8601 datetime to schedule the SMS notification. |
| `from` | string | Override the sender phone number. Must be a dedicated number on your Pingram account. |

## Templates\#

### templates\_create\_template()\#

Create a new template for a notification

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    channel = 'channel_example'

    template_post_request = TemplatePostRequest()

    response = await client.templates.templates_create_template(notification_id, channel, template_post_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | Notification ID |  |
| **channel** | **str** | Channel type |  |
| **template\_post\_request** | **TemplatePostRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `templateId` | string | (required) Unique ID for this template within the notification and channel. Required. |
| `html` | string | HTML body of the email. |
| `previewText` | string | Preview text (e.g. for inbox). |
| `internal` | string | Internal editor representation of the email content (e.g. Bee or Redactor JSON). Used for editing and component embedding; the actual email sent to recipients uses the html field. |
| `subject` | string | Email subject line. |
| `senderName` | string | Sender display name. |
| `senderEmail` | string | Sender email address. |
| `title` | string | Notification title (in-app). |
| `redirectURL` | string | URL to open when the user taps the notification. |
| `imageURL` | string | Image URL shown in the in-app notification. |
| `instant` | object | Copy for instant (real-time) delivery. |
| `instant.title` | string |  |
| `instant.redirectURL` | string |  |
| `instant.imageURL` | string | (required) |
| `batch` | object | Copy for batch delivery. |
| `batch.title` | string | (required) |
| `batch.redirectURL` | string | (required) |
| `batch.imageURL` | string | (required) |
| `text` | string | Message text (SMS or call). |
| `message` | string | Push notification body text. (title is shared with INAPP\_WEB above.) |
| `icon` | string | Web push: icon URL. Slack: bot icon (emoji or URL). |
| `url` | string | Web push: URL to open when the notification is clicked. |
| `blocks` | Record<string, any>\[\] | Slack message blocks (optional). |
| `username` | string | Slack bot username. |

### templates\_delete\_template()\#

Delete a template

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    channel = 'channel_example'

    template_id = 'template_id_example'

    response = await client.templates.templates_delete_template(notification_id, channel, template_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | Notification ID |  |
| **channel** | **str** | Channel type |  |
| **template\_id** | **str** | Template ID |  |

### templates\_get\_template()\#

Get a single template by ID

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    channel = 'channel_example'

    template_id = 'template_id_example'

    response = await client.templates.templates_get_template(notification_id, channel, template_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | Notification ID |  |
| **channel** | **str** | Channel type |  |
| **template\_id** | **str** | Template ID |  |

### templates\_list\_templates()\#

List all templates for a notification and channel

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    channel = 'channel_example'

    response = await client.templates.templates_list_templates(notification_id, channel)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | Notification ID |  |
| **channel** | **str** | Channel type |  |

### templates\_set\_default\_template()\#

Set a template as default for specific delivery modes

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    channel = 'channel_example'

    set_default_template_request = SetDefaultTemplateRequest()

    response = await client.templates.templates_set_default_template(notification_id, channel, set_default_template_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | Notification ID |  |
| **channel** | **str** | Channel type |  |
| **set\_default\_template\_request** | **SetDefaultTemplateRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `templateId` | string | (required) |
| `modes` | (“instant” \| “hourly” \| “daily” \| “weekly” \| “monthly”)\[\] | (required) |

### templates\_update\_template()\#

Update a template’s properties

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    channel = 'channel_example'

    template_id = 'template_id_example'

    template_patch_request = TemplatePatchRequest()

    response = await client.templates.templates_update_template(notification_id, channel, template_id, template_patch_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | Notification ID |  |
| **channel** | **str** | Channel type |  |
| **template\_id** | **str** | Template ID |  |
| **template\_patch\_request** | **TemplatePatchRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `html` | string | HTML body of the email. |
| `previewText` | string | Preview text (e.g. for inbox). |
| `internal` | string | Internal editor representation of the email content (e.g. Bee or Redactor JSON). Used for editing and component embedding; the actual email sent to recipients uses the html field. |
| `subject` | string | Email subject line. |
| `senderName` | string | Sender display name. |
| `senderEmail` | string | Sender email address. |
| `title` | string | Notification title (in-app). |
| `redirectURL` | string | URL to open when the user taps the notification. |
| `imageURL` | string | Image URL shown in the in-app notification. |
| `instant` | object | Copy for instant (real-time) delivery. |
| `instant.title` | string |  |
| `instant.redirectURL` | string |  |
| `instant.imageURL` | string | (required) |
| `batch` | object | Copy for batch delivery. |
| `batch.title` | string | (required) |
| `batch.redirectURL` | string | (required) |
| `batch.imageURL` | string | (required) |
| `text` | string | Message text (SMS or call). |
| `message` | string | Push notification body text. (title is shared with INAPP\_WEB above.) |
| `icon` | string | Web push: icon URL. Slack: bot icon (emoji or URL). |
| `url` | string | Web push: URL to open when the notification is clicked. |
| `blocks` | Record<string, any>\[\] | Slack message blocks (optional). |
| `username` | string | Slack bot username. |

## Types\#

### types\_create\_notification\_type()\#

Create a new notification

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_create_request = NotificationCreateRequest()

    response = await client.types.types_create_notification_type(notification_create_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_create\_request** | **NotificationCreateRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `notificationId` | string | (required) |
| `title` | string | (required) |
| `channels` | string\[\] | (required) |
| `options` | object |  |
| `options.EMAIL` | object |  |
| `options.EMAIL.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.EMAIL.off` | object |  |
| `options.EMAIL.off.enabled` | boolean | (required) |
| `options.EMAIL.instant` | object |  |
| `options.EMAIL.instant.enabled` | boolean | (required) |
| `options.EMAIL.hourly` | object |  |
| `options.EMAIL.hourly.enabled` | boolean | (required) |
| `options.EMAIL.daily` | object |  |
| `options.EMAIL.daily.enabled` | boolean | (required) |
| `options.EMAIL.daily.hour` | string |  |
| `options.EMAIL.weekly` | object |  |
| `options.EMAIL.weekly.enabled` | boolean | (required) |
| `options.EMAIL.weekly.hour` | string |  |
| `options.EMAIL.weekly.day` | string |  |
| `options.EMAIL.monthly` | object |  |
| `options.EMAIL.monthly.enabled` | boolean | (required) |
| `options.EMAIL.monthly.hour` | string |  |
| `options.EMAIL.monthly.date` | “first” \| “last” |  |
| `options.INAPP_WEB` | object |  |
| `options.INAPP_WEB.defaultDeliveryOption` | “off” \| “instant” | (required) |
| `options.INAPP_WEB.off` | object |  |
| `options.INAPP_WEB.off.enabled` | boolean | (required) |
| `options.INAPP_WEB.instant` | object |  |
| `options.INAPP_WEB.instant.enabled` | boolean | (required) |
| `options.INAPP_WEB.instant.batching` | boolean |  |
| `options.INAPP_WEB.instant.batchingKey` | string |  |
| `options.INAPP_WEB.instant.batchingWindow` | number |  |
| `options.SMS` | object |  |
| `options.SMS.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.SMS.off` | object |  |
| `options.SMS.off.enabled` | boolean | (required) |
| `options.SMS.instant` | object |  |
| `options.SMS.instant.enabled` | boolean | (required) |
| `options.SMS.hourly` | object |  |
| `options.SMS.hourly.enabled` | boolean | (required) |
| `options.SMS.daily` | object |  |
| `options.SMS.daily.enabled` | boolean | (required) |
| `options.SMS.daily.hour` | string |  |
| `options.SMS.weekly` | object |  |
| `options.SMS.weekly.enabled` | boolean | (required) |
| `options.SMS.weekly.hour` | string |  |
| `options.SMS.weekly.day` | string |  |
| `options.SMS.monthly` | object |  |
| `options.SMS.monthly.enabled` | boolean | (required) |
| `options.SMS.monthly.hour` | string |  |
| `options.SMS.monthly.date` | “first” \| “last” |  |
| `options.CALL` | object |  |
| `options.CALL.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.CALL.off` | object |  |
| `options.CALL.off.enabled` | boolean | (required) |
| `options.CALL.instant` | object |  |
| `options.CALL.instant.enabled` | boolean | (required) |
| `options.CALL.hourly` | object |  |
| `options.CALL.hourly.enabled` | boolean | (required) |
| `options.CALL.daily` | object |  |
| `options.CALL.daily.enabled` | boolean | (required) |
| `options.CALL.daily.hour` | string |  |
| `options.CALL.weekly` | object |  |
| `options.CALL.weekly.enabled` | boolean | (required) |
| `options.CALL.weekly.hour` | string |  |
| `options.CALL.weekly.day` | string |  |
| `options.CALL.monthly` | object |  |
| `options.CALL.monthly.enabled` | boolean | (required) |
| `options.CALL.monthly.hour` | string |  |
| `options.CALL.monthly.date` | “first” \| “last” |  |
| `options.VOICE` | object |  |
| `options.VOICE.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.VOICE.off` | object |  |
| `options.VOICE.off.enabled` | boolean | (required) |
| `options.VOICE.instant` | object |  |
| `options.VOICE.instant.enabled` | boolean | (required) |
| `options.VOICE.hourly` | object |  |
| `options.VOICE.hourly.enabled` | boolean | (required) |
| `options.VOICE.daily` | object |  |
| `options.VOICE.daily.enabled` | boolean | (required) |
| `options.VOICE.daily.hour` | string |  |
| `options.VOICE.weekly` | object |  |
| `options.VOICE.weekly.enabled` | boolean | (required) |
| `options.VOICE.weekly.hour` | string |  |
| `options.VOICE.weekly.day` | string |  |
| `options.VOICE.monthly` | object |  |
| `options.VOICE.monthly.enabled` | boolean | (required) |
| `options.VOICE.monthly.hour` | string |  |
| `options.VOICE.monthly.date` | “first” \| “last” |  |
| `options.PUSH` | object |  |
| `options.PUSH.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.PUSH.off` | object |  |
| `options.PUSH.off.enabled` | boolean | (required) |
| `options.PUSH.instant` | object |  |
| `options.PUSH.instant.enabled` | boolean | (required) |
| `options.PUSH.hourly` | object |  |
| `options.PUSH.hourly.enabled` | boolean | (required) |
| `options.PUSH.daily` | object |  |
| `options.PUSH.daily.enabled` | boolean | (required) |
| `options.PUSH.daily.hour` | string |  |
| `options.PUSH.weekly` | object |  |
| `options.PUSH.weekly.enabled` | boolean | (required) |
| `options.PUSH.weekly.hour` | string |  |
| `options.PUSH.weekly.day` | string |  |
| `options.PUSH.monthly` | object |  |
| `options.PUSH.monthly.enabled` | boolean | (required) |
| `options.PUSH.monthly.hour` | string |  |
| `options.PUSH.monthly.date` | “first” \| “last” |  |
| `options.WEB_PUSH` | object |  |
| `options.WEB_PUSH.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.WEB_PUSH.off` | object |  |
| `options.WEB_PUSH.off.enabled` | boolean | (required) |
| `options.WEB_PUSH.instant` | object |  |
| `options.WEB_PUSH.instant.enabled` | boolean | (required) |
| `options.WEB_PUSH.hourly` | object |  |
| `options.WEB_PUSH.hourly.enabled` | boolean | (required) |
| `options.WEB_PUSH.daily` | object |  |
| `options.WEB_PUSH.daily.enabled` | boolean | (required) |
| `options.WEB_PUSH.daily.hour` | string |  |
| `options.WEB_PUSH.weekly` | object |  |
| `options.WEB_PUSH.weekly.enabled` | boolean | (required) |
| `options.WEB_PUSH.weekly.hour` | string |  |
| `options.WEB_PUSH.weekly.day` | string |  |
| `options.WEB_PUSH.monthly` | object |  |
| `options.WEB_PUSH.monthly.enabled` | boolean | (required) |
| `options.WEB_PUSH.monthly.hour` | string |  |
| `options.WEB_PUSH.monthly.date` | “first” \| “last” |  |
| `options.SLACK` | object |  |
| `options.SLACK.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.SLACK.off` | object |  |
| `options.SLACK.off.enabled` | boolean | (required) |
| `options.SLACK.instant` | object |  |
| `options.SLACK.instant.enabled` | boolean | (required) |
| `options.SLACK.hourly` | object |  |
| `options.SLACK.hourly.enabled` | boolean | (required) |
| `options.SLACK.daily` | object |  |
| `options.SLACK.daily.enabled` | boolean | (required) |
| `options.SLACK.daily.hour` | string |  |
| `options.SLACK.weekly` | object |  |
| `options.SLACK.weekly.enabled` | boolean | (required) |
| `options.SLACK.weekly.hour` | string |  |
| `options.SLACK.weekly.day` | string |  |
| `options.SLACK.monthly` | object |  |
| `options.SLACK.monthly.enabled` | boolean | (required) |
| `options.SLACK.monthly.hour` | string |  |
| `options.SLACK.monthly.date` | “first” \| “last” |  |

### types\_delete\_notification\_type()\#

Delete a notification

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    response = await client.types.types_delete_notification_type(notification_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | The notification ID |  |

### types\_get\_notification\_type()\#

Get a specific notification by ID

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    response = await client.types.types_get_notification_type(notification_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | The notification ID |  |

### types\_list\_notification\_types()\#

Get all notifications for an account with their templates

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.types.types_list_notification_types()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### types\_update\_notification\_type()\#

Update a notification’s settings

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    notification_id = 'notification_id_example'

    notification_patch_request = NotificationPatchRequest()

    response = await client.types.types_update_notification_type(notification_id, notification_patch_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **notification\_id** | **str** | The notification ID |  |
| **notification\_patch\_request** | **NotificationPatchRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `title` | string |  |
| `channels` | (“EMAIL” \| “INAPP\_WEB” \| “SMS” \| “CALL” \| “VOICE” \| “PUSH” \| “WEB\_PUSH” \| “SLACK”)\[\] |  |
| `enabled` | boolean |  |
| `deduplication` | object |  |
| `deduplication.duration` | number | (required) |
| `throttling` | object |  |
| `throttling.max` | number | (required) |
| `throttling.period` | number | (required) |
| `throttling.unit` | “seconds” \| “minutes” \| “hours” \| “days” \| “months” \| “years” | (required) |
| `throttling.forever` | boolean | (required) |
| `throttling.scope` | (“userId” \| “notificationId”)\[\] | (required) |
| `retention` | number | null |
| `options` | object |  |
| `options.EMAIL` | object |  |
| `options.EMAIL.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.EMAIL.off` | object |  |
| `options.EMAIL.off.enabled` | boolean | (required) |
| `options.EMAIL.instant` | object |  |
| `options.EMAIL.instant.enabled` | boolean | (required) |
| `options.EMAIL.hourly` | object |  |
| `options.EMAIL.hourly.enabled` | boolean | (required) |
| `options.EMAIL.daily` | object |  |
| `options.EMAIL.daily.enabled` | boolean | (required) |
| `options.EMAIL.daily.hour` | string |  |
| `options.EMAIL.weekly` | object |  |
| `options.EMAIL.weekly.enabled` | boolean | (required) |
| `options.EMAIL.weekly.hour` | string |  |
| `options.EMAIL.weekly.day` | string |  |
| `options.EMAIL.monthly` | object |  |
| `options.EMAIL.monthly.enabled` | boolean | (required) |
| `options.EMAIL.monthly.hour` | string |  |
| `options.EMAIL.monthly.date` | “first” \| “last” |  |
| `options.INAPP_WEB` | object |  |
| `options.INAPP_WEB.defaultDeliveryOption` | “off” \| “instant” | (required) |
| `options.INAPP_WEB.off` | object |  |
| `options.INAPP_WEB.off.enabled` | boolean | (required) |
| `options.INAPP_WEB.instant` | object |  |
| `options.INAPP_WEB.instant.enabled` | boolean | (required) |
| `options.INAPP_WEB.instant.batching` | boolean |  |
| `options.INAPP_WEB.instant.batchingKey` | string |  |
| `options.INAPP_WEB.instant.batchingWindow` | number |  |
| `options.SMS` | object |  |
| `options.SMS.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.SMS.off` | object |  |
| `options.SMS.off.enabled` | boolean | (required) |
| `options.SMS.instant` | object |  |
| `options.SMS.instant.enabled` | boolean | (required) |
| `options.SMS.hourly` | object |  |
| `options.SMS.hourly.enabled` | boolean | (required) |
| `options.SMS.daily` | object |  |
| `options.SMS.daily.enabled` | boolean | (required) |
| `options.SMS.daily.hour` | string |  |
| `options.SMS.weekly` | object |  |
| `options.SMS.weekly.enabled` | boolean | (required) |
| `options.SMS.weekly.hour` | string |  |
| `options.SMS.weekly.day` | string |  |
| `options.SMS.monthly` | object |  |
| `options.SMS.monthly.enabled` | boolean | (required) |
| `options.SMS.monthly.hour` | string |  |
| `options.SMS.monthly.date` | “first” \| “last” |  |
| `options.CALL` | object |  |
| `options.CALL.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.CALL.off` | object |  |
| `options.CALL.off.enabled` | boolean | (required) |
| `options.CALL.instant` | object |  |
| `options.CALL.instant.enabled` | boolean | (required) |
| `options.CALL.hourly` | object |  |
| `options.CALL.hourly.enabled` | boolean | (required) |
| `options.CALL.daily` | object |  |
| `options.CALL.daily.enabled` | boolean | (required) |
| `options.CALL.daily.hour` | string |  |
| `options.CALL.weekly` | object |  |
| `options.CALL.weekly.enabled` | boolean | (required) |
| `options.CALL.weekly.hour` | string |  |
| `options.CALL.weekly.day` | string |  |
| `options.CALL.monthly` | object |  |
| `options.CALL.monthly.enabled` | boolean | (required) |
| `options.CALL.monthly.hour` | string |  |
| `options.CALL.monthly.date` | “first” \| “last” |  |
| `options.VOICE` | object |  |
| `options.VOICE.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.VOICE.off` | object |  |
| `options.VOICE.off.enabled` | boolean | (required) |
| `options.VOICE.instant` | object |  |
| `options.VOICE.instant.enabled` | boolean | (required) |
| `options.VOICE.hourly` | object |  |
| `options.VOICE.hourly.enabled` | boolean | (required) |
| `options.VOICE.daily` | object |  |
| `options.VOICE.daily.enabled` | boolean | (required) |
| `options.VOICE.daily.hour` | string |  |
| `options.VOICE.weekly` | object |  |
| `options.VOICE.weekly.enabled` | boolean | (required) |
| `options.VOICE.weekly.hour` | string |  |
| `options.VOICE.weekly.day` | string |  |
| `options.VOICE.monthly` | object |  |
| `options.VOICE.monthly.enabled` | boolean | (required) |
| `options.VOICE.monthly.hour` | string |  |
| `options.VOICE.monthly.date` | “first” \| “last” |  |
| `options.PUSH` | object |  |
| `options.PUSH.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.PUSH.off` | object |  |
| `options.PUSH.off.enabled` | boolean | (required) |
| `options.PUSH.instant` | object |  |
| `options.PUSH.instant.enabled` | boolean | (required) |
| `options.PUSH.hourly` | object |  |
| `options.PUSH.hourly.enabled` | boolean | (required) |
| `options.PUSH.daily` | object |  |
| `options.PUSH.daily.enabled` | boolean | (required) |
| `options.PUSH.daily.hour` | string |  |
| `options.PUSH.weekly` | object |  |
| `options.PUSH.weekly.enabled` | boolean | (required) |
| `options.PUSH.weekly.hour` | string |  |
| `options.PUSH.weekly.day` | string |  |
| `options.PUSH.monthly` | object |  |
| `options.PUSH.monthly.enabled` | boolean | (required) |
| `options.PUSH.monthly.hour` | string |  |
| `options.PUSH.monthly.date` | “first” \| “last” |  |
| `options.WEB_PUSH` | object |  |
| `options.WEB_PUSH.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.WEB_PUSH.off` | object |  |
| `options.WEB_PUSH.off.enabled` | boolean | (required) |
| `options.WEB_PUSH.instant` | object |  |
| `options.WEB_PUSH.instant.enabled` | boolean | (required) |
| `options.WEB_PUSH.hourly` | object |  |
| `options.WEB_PUSH.hourly.enabled` | boolean | (required) |
| `options.WEB_PUSH.daily` | object |  |
| `options.WEB_PUSH.daily.enabled` | boolean | (required) |
| `options.WEB_PUSH.daily.hour` | string |  |
| `options.WEB_PUSH.weekly` | object |  |
| `options.WEB_PUSH.weekly.enabled` | boolean | (required) |
| `options.WEB_PUSH.weekly.hour` | string |  |
| `options.WEB_PUSH.weekly.day` | string |  |
| `options.WEB_PUSH.monthly` | object |  |
| `options.WEB_PUSH.monthly.enabled` | boolean | (required) |
| `options.WEB_PUSH.monthly.hour` | string |  |
| `options.WEB_PUSH.monthly.date` | “first” \| “last” |  |
| `options.SLACK` | object |  |
| `options.SLACK.defaultDeliveryOption` | “off” \| “instant” \| “hourly” \| “daily” \| “weekly” \| “monthly” | (required) |
| `options.SLACK.off` | object |  |
| `options.SLACK.off.enabled` | boolean | (required) |
| `options.SLACK.instant` | object |  |
| `options.SLACK.instant.enabled` | boolean | (required) |
| `options.SLACK.hourly` | object |  |
| `options.SLACK.hourly.enabled` | boolean | (required) |
| `options.SLACK.daily` | object |  |
| `options.SLACK.daily.enabled` | boolean | (required) |
| `options.SLACK.daily.hour` | string |  |
| `options.SLACK.weekly` | object |  |
| `options.SLACK.weekly.enabled` | boolean | (required) |
| `options.SLACK.weekly.hour` | string |  |
| `options.SLACK.weekly.day` | string |  |
| `options.SLACK.monthly` | object |  |
| `options.SLACK.monthly.enabled` | boolean | (required) |
| `options.SLACK.monthly.hour` | string |  |
| `options.SLACK.monthly.date` | “first” \| “last” |  |

## User\#

### user\_generate\_slack\_oauth\_path()\#

Complete Slack OAuth flow and store access token for user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    user_id = 'user_id_example'

    slack_oauth_request = SlackOauthRequest()

    response = await client.user.user_generate_slack_oauth_path(user_id, slack_oauth_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **user\_id** | **str** | User ID |  |
| **slack\_oauth\_request** | **SlackOauthRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `code` | string | (required) |
| `redirect_uri` | string | (required) |

### user\_get\_account\_metadata()\#

Get account-level metadata including logo, VAPID key, and web push status

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.user.user_get_account_metadata()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### user\_get\_available\_slack\_channels()\#

Get list of Slack channels and users for the authenticated user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    user_id = 'user_id_example'

    response = await client.user.user_get_available_slack_channels(user_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **user\_id** | **str** | User ID |  |

### user\_get\_in\_app\_notifications()\#

Get in-app notifications for a user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    before = 'before_example'

    count = 3.4

    response = await client.user.user_get_in_app_notifications(before=before, count=count)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **before** | **str** | Timestamp or ISO date to fetch notifications before | \[optional\] |
| **count** | **float** | Number of notifications to return (default 10) | \[optional\] |

### user\_get\_in\_app\_unread\_count()\#

Get the count of unread in-app notifications for a user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.user.user_get_in_app_unread_count()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### user\_get\_user()\#

Get a user by ID. All users exist implicitly, returns basic user object if not found in DB.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    user_id = 'user_id_example'

    response = await client.user.user_get_user(user_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **user\_id** | **str** | User ID |  |

### user\_identify()\#

Create or update a user with the given ID. Updates lastSeenTime automatically.

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    user_id = 'user_id_example'

    post_user_request = PostUserRequest()

    response = await client.user.user_identify(user_id, post_user_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **user\_id** | **str** | User ID |  |
| **post\_user\_request** | **PostUserRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `id` | string | Unique user identifier. Required. |
| `email` | string | User’s email address for email notifications. |
| `number` | string | User’s phone number for SMS/call notifications. |
| `pushTokens` | object\[\] | Mobile push tokens (FCM, APN) for push notifications. |
| `pushTokens[].type` | “FCM” \| “APN” | (required) |
| `pushTokens[].token` | string | (required) |
| `pushTokens[].device` | object | (required) |
| `pushTokens[].device.app_id` | string |  |
| `pushTokens[].device.ad_id` | string |  |
| `pushTokens[].device.device_id` | string | (required) |
| `pushTokens[].device.platform` | string |  |
| `pushTokens[].device.manufacturer` | string |  |
| `pushTokens[].device.model` | string |  |
| `pushTokens[].environment` | string | used by APN to differentiate between sandbox and production builds (sandbox/undefined or production) |
| `webPushTokens` | object\[\] | Web push subscription config from the browser. |
| `webPushTokens[].sub` | object | (required) Configuration for a Push Subscription. This can be obtained on the frontend by calling serviceWorkerRegistration.pushManager.subscribe(). The expected format is the same output as JSON.stringify’ing a PushSubscription in the browser. |
| `webPushTokens[].sub.endpoint` | string | (required) |
| `webPushTokens[].sub.keys` | object | (required) |
| `webPushTokens[].sub.keys.p256dh` | string | (required) |
| `webPushTokens[].sub.keys.auth` | string | (required) |
| `timezone` | string | User’s timezone (e.g. “America/New\_York”) for scheduling. |
| `slackChannel` | string | The destination channel of slack notifications sent to this user. Can be either of the following: - Channel name, e.g. “test” - Channel name with # prefix, e.g. “#test” - Channel ID, e.g. “C1234567890” - User ID for DM, e.g. “U1234567890” - Username with @ prefix, e.g. “@test” |
| `slackToken` | object |  |
| `slackToken.access_token` | string |  |
| `slackToken.app_id` | string |  |
| `slackToken.authed_user` | object |  |
| `slackToken.authed_user.access_token` | string |  |
| `slackToken.authed_user.expires_in` | number |  |
| `slackToken.authed_user.id` | string |  |
| `slackToken.authed_user.refresh_token` | string |  |
| `slackToken.authed_user.scope` | string |  |
| `slackToken.authed_user.token_type` | string |  |
| `slackToken.bot_user_id` | string |  |
| `slackToken.enterprise` | object |  |
| `slackToken.enterprise.id` | string |  |
| `slackToken.enterprise.name` | string |  |
| `slackToken.error` | string |  |
| `slackToken.expires_in` | number |  |
| `slackToken.incoming_webhook` | object |  |
| `slackToken.incoming_webhook.channel` | string |  |
| `slackToken.incoming_webhook.channel_id` | string |  |
| `slackToken.incoming_webhook.configuration_url` | string |  |
| `slackToken.incoming_webhook.url` | string |  |
| `slackToken.is_enterprise_install` | boolean |  |
| `slackToken.needed` | string |  |
| `slackToken.ok` | boolean | (required) |
| `slackToken.provided` | string |  |
| `slackToken.refresh_token` | string |  |
| `slackToken.scope` | string |  |
| `slackToken.team` | object |  |
| `slackToken.team.id` | string |  |
| `slackToken.team.name` | string |  |
| `slackToken.token_type` | string |  |
| `slackToken.warning` | string |  |
| `slackToken.response_metadata` | object |  |
| `slackToken.response_metadata.warnings` | string\[\] |  |
| `slackToken.response_metadata.next_cursor` | string |  |
| `slackToken.response_metadata.scopes` | string\[\] |  |
| `slackToken.response_metadata.acceptedScopes` | string\[\] |  |
| `slackToken.response_metadata.retryAfter` | number |  |
| `slackToken.response_metadata.messages` | string\[\] |  |

### user\_mark\_in\_app\_notifications\_as\_seen()\#

Mark in-app web notifications as seen/read for a user

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    in_app_notification_unread_clear_request = InAppNotificationUnreadClearRequest()

    response = await client.user.user_mark_in_app_notifications_as_seen(in_app_notification_unread_clear_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **in\_app\_notification\_unread\_clear\_request** | **InAppNotificationUnreadClearRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `notificationId` | string |  |
| `trackingId` | string |  |

### user\_update\_in\_app\_notification\_status()\#

Update in-app web notification status (opened, archived, clicked, etc.)

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    in_app_notification_patch_request = InAppNotificationPatchRequest()

    response = await client.user.user_update_in_app_notification_status(in_app_notification_patch_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **in\_app\_notification\_patch\_request** | **InAppNotificationPatchRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `trackingIds` | string\[\] | (required) |
| `opened` | string |  |
| `clicked` | string |  |
| `archived` | string |  |
| `actioned1` | string |  |
| `actioned2` | string |  |
| `reply` | object |  |
| `reply.date` | string | (required) |
| `reply.message` | string | (required) |
| `replies` | object\[\] |  |
| `replies[].date` | string | (required) |
| `replies[].message` | string | (required) |

## Users\#

### users\_delete\_user()\#

Delete a user and all associated data (in-app notifications, preferences, and user record)

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    user_id = 'user_id_example'

    env_id = 'env_id_example'

    response = await client.users.users_delete_user(user_id, env_id=env_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **user\_id** | **str** | User ID |  |
| **env\_id** | **str** | Environment ID (required when using JWT auth) | \[optional\] |

### users\_list\_users()\#

Get all users for an environment with pagination support

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    limit = 3.4

    next_token = 'next_token_example'

    env_id = 'env_id_example'

    response = await client.users.users_list_users(limit, next_token, env_id=env_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **limit** | **float** | Maximum number of users to return (default |  |
| **next\_token** | **str** | Pagination token for next page |  |
| **env\_id** | **str** | Environment ID (required when using JWT auth) | \[optional\] |

### users\_remove\_user\_from\_suppression()\#

Remove user suppression status for a specific channel

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    user_id = 'user_id_example'

    channel = 'channel_example'

    env_id = 'env_id_example'

    response = await client.users.users_remove_user_from_suppression(user_id, channel, env_id=env_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **user\_id** | **str** | User ID |  |
| **channel** | **str** | Channel type (EMAIL) |  |
| **env\_id** | **str** | Environment ID (required when using JWT auth) | \[optional\] |

## Voice\#

### voice\_bind\_number()\#

Bind a phone number to a deployed agent for inbound routing

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    agent_id = 'agent_id_example'

    bind_number_request = BindNumberRequest()

    response = await client.voice.voice_bind_number(agent_id, bind_number_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **agent\_id** | **str** | Agent id |  |
| **bind\_number\_request** | **BindNumberRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `phoneNumber` | string | (required) |

### voice\_call()\#

Place an outbound call with an inline agent spec (ephemeral)

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    voice_call_request = VoiceCallRequest()

    response = await client.voice.voice_call(voice_call_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **voice\_call\_request** | **VoiceCallRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `phoneNumber` | string | (required) |
| `spec` | object | (required) |
| `spec.name` | string | (required) |
| `spec.instructions` | string | (required) |
| `spec.inbound` | object | (required) |
| `spec.inbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.inbound.greeting` | string | (required) |
| `spec.outbound` | object | (required) |
| `spec.outbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.outbound.opener` | string | (required) |
| `spec.outbound.voicemailAction` | “hangup” \| “message” \| “continue” | (required) |
| `spec.outbound.voicemailMessage` | string |  |
| `spec.model` | object \| object | (required) Speech pipeline. Prefer s2s mode (e.g. `openai:gpt-realtime` with voice `marin`). |
| `spec.model.mode` | “chained” | (required) |
| `spec.model.llm` | string | (required) ‘provider:model’, e.g. ‘openai:gpt-4o’ |
| `spec.model.stt` | string | (required) ‘provider:model’, e.g. ‘deepgram:nova-3’ |
| `spec.model.tts` | string | (required) ‘provider:model’, e.g. ‘elevenlabs:eleven\_multilingual\_v2’ |
| `spec.model.voiceId` | string | (required) Provider-native voice id for the selected TTS provider (e.g. ElevenLabs UUID, OpenAI `alloy`). |
| `spec.model.language` | string | (required) |
| `spec.model.speechSpeed` | number | (required) |
| `spec.model.temperature` | number | (required) |
| `spec.model.maxTokens` | number | (required) |
| `spec.tools` | (object \| object \| object \| object \| object)\[\] | (required) |
| `spec.variables` | object\[\] | (required) |
| `spec.variables[].name` | string | (required) |
| `spec.variables[].description` | string |  |
| `spec.variables[].defaultValue` | string |  |
| `spec.conversation` | object | (required) |
| `spec.conversation.turnDetection` | “semantic” \| “vad” | (required) |
| `spec.conversation.minEndOfTurnSilenceMs` | number | (required) |
| `spec.conversation.allowInterruptions` | boolean | (required) |
| `spec.conversation.minInterruptionDurationMs` | number | (required) |
| `spec.conversation.silenceTimeoutSeconds` | number | (required) |
| `spec.conversation.maxCallLengthSeconds` | number | (required) |
| `spec.conversation.agentCanEndCall` | boolean | When true (default), the agent may invoke the built-in end\_call action. |
| `spec.compliance` | object | (required) |
| `spec.compliance.recordingEnabled` | boolean | (required) |
| `variables` | Record<string, string> | Optional per-call {{variable}} overrides. |
| `agentId` | string | Saved agent id when testing from the dashboard playground. |

### voice\_create\_agent()\#

Deploy a voice agent (persist spec for production routing)

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    create_voice_agent_request = CreateVoiceAgentRequest()

    response = await client.voice.voice_create_agent(create_voice_agent_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **create\_voice\_agent\_request** | **CreateVoiceAgentRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `spec` | object | (required) |
| `spec.name` | string | (required) |
| `spec.instructions` | string | (required) |
| `spec.inbound` | object | (required) |
| `spec.inbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.inbound.greeting` | string | (required) |
| `spec.outbound` | object | (required) |
| `spec.outbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.outbound.opener` | string | (required) |
| `spec.outbound.voicemailAction` | “hangup” \| “message” \| “continue” | (required) |
| `spec.outbound.voicemailMessage` | string |  |
| `spec.model` | object \| object | (required) Speech pipeline. Prefer s2s mode (e.g. `openai:gpt-realtime` with voice `marin`). |
| `spec.model.mode` | “chained” | (required) |
| `spec.model.llm` | string | (required) ‘provider:model’, e.g. ‘openai:gpt-4o’ |
| `spec.model.stt` | string | (required) ‘provider:model’, e.g. ‘deepgram:nova-3’ |
| `spec.model.tts` | string | (required) ‘provider:model’, e.g. ‘elevenlabs:eleven\_multilingual\_v2’ |
| `spec.model.voiceId` | string | (required) Provider-native voice id for the selected TTS provider (e.g. ElevenLabs UUID, OpenAI `alloy`). |
| `spec.model.language` | string | (required) |
| `spec.model.speechSpeed` | number | (required) |
| `spec.model.temperature` | number | (required) |
| `spec.model.maxTokens` | number | (required) |
| `spec.tools` | (object \| object \| object \| object \| object)\[\] | (required) |
| `spec.variables` | object\[\] | (required) |
| `spec.variables[].name` | string | (required) |
| `spec.variables[].description` | string |  |
| `spec.variables[].defaultValue` | string |  |
| `spec.conversation` | object | (required) |
| `spec.conversation.turnDetection` | “semantic” \| “vad” | (required) |
| `spec.conversation.minEndOfTurnSilenceMs` | number | (required) |
| `spec.conversation.allowInterruptions` | boolean | (required) |
| `spec.conversation.minInterruptionDurationMs` | number | (required) |
| `spec.conversation.silenceTimeoutSeconds` | number | (required) |
| `spec.conversation.maxCallLengthSeconds` | number | (required) |
| `spec.conversation.agentCanEndCall` | boolean | When true (default), the agent may invoke the built-in end\_call action. |
| `spec.compliance` | object | (required) |
| `spec.compliance.recordingEnabled` | boolean | (required) |

### voice\_create\_browser\_call()\#

Place an ephemeral browser playground call with an inline agent spec

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    voice_browser_call_request = VoiceBrowserCallRequest()

    response = await client.voice.voice_create_browser_call(voice_browser_call_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **voice\_browser\_call\_request** | **VoiceBrowserCallRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `spec` | object | (required) |
| `spec.name` | string | (required) |
| `spec.instructions` | string | (required) |
| `spec.inbound` | object | (required) |
| `spec.inbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.inbound.greeting` | string | (required) |
| `spec.outbound` | object | (required) |
| `spec.outbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.outbound.opener` | string | (required) |
| `spec.outbound.voicemailAction` | “hangup” \| “message” \| “continue” | (required) |
| `spec.outbound.voicemailMessage` | string |  |
| `spec.model` | object \| object | (required) Speech pipeline. Prefer s2s mode (e.g. `openai:gpt-realtime` with voice `marin`). |
| `spec.model.mode` | “chained” | (required) |
| `spec.model.llm` | string | (required) ‘provider:model’, e.g. ‘openai:gpt-4o’ |
| `spec.model.stt` | string | (required) ‘provider:model’, e.g. ‘deepgram:nova-3’ |
| `spec.model.tts` | string | (required) ‘provider:model’, e.g. ‘elevenlabs:eleven\_multilingual\_v2’ |
| `spec.model.voiceId` | string | (required) Provider-native voice id for the selected TTS provider (e.g. ElevenLabs UUID, OpenAI `alloy`). |
| `spec.model.language` | string | (required) |
| `spec.model.speechSpeed` | number | (required) |
| `spec.model.temperature` | number | (required) |
| `spec.model.maxTokens` | number | (required) |
| `spec.tools` | (object \| object \| object \| object \| object)\[\] | (required) |
| `spec.variables` | object\[\] | (required) |
| `spec.variables[].name` | string | (required) |
| `spec.variables[].description` | string |  |
| `spec.variables[].defaultValue` | string |  |
| `spec.conversation` | object | (required) |
| `spec.conversation.turnDetection` | “semantic” \| “vad” | (required) |
| `spec.conversation.minEndOfTurnSilenceMs` | number | (required) |
| `spec.conversation.allowInterruptions` | boolean | (required) |
| `spec.conversation.minInterruptionDurationMs` | number | (required) |
| `spec.conversation.silenceTimeoutSeconds` | number | (required) |
| `spec.conversation.maxCallLengthSeconds` | number | (required) |
| `spec.conversation.agentCanEndCall` | boolean | When true (default), the agent may invoke the built-in end\_call action. |
| `spec.compliance` | object | (required) |
| `spec.compliance.recordingEnabled` | boolean | (required) |
| `variables` | Record<string, string> | Optional per-call {{variable}} overrides for browser playground. |
| `agentId` | string | Saved agent id when testing from the dashboard playground. |

### voice\_delete\_agent()\#

Remove a deployed voice agent and unbind its numbers

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    agent_id = 'agent_id_example'

    response = await client.voice.voice_delete_agent(agent_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **agent\_id** | **str** | Agent id |  |

### voice\_get\_agent()\#

Get a deployed voice agent

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    agent_id = 'agent_id_example'

    response = await client.voice.voice_get_agent(agent_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **agent\_id** | **str** | Agent id |  |

### voice\_get\_call()\#

Get a call with transcript timeline and recording playback URL

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    tracking_id = 'tracking_id_example'

    response = await client.voice.voice_get_call(tracking_id)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **tracking\_id** | **str** | Call tracking id |  |

### voice\_list\_agents()\#

List deployed voice agents for the account

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    response = await client.voice.voice_list_agents()

    print(response)
```

#### Parameters\#

This endpoint does not need any parameter.

### voice\_list\_calls()\#

List recent calls newest-first (30-day retention)

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    agent_id = 'agent_id_example'

    limit = 3.4

    cursor = 'cursor_example'

    response = await client.voice.voice_list_calls(agent_id=agent_id, limit=limit, cursor=cursor)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **agent\_id** | **str** | Only calls handled by this agent | \[optional\] |
| **limit** | **float** | Page size (default 25, max 100) | \[optional\] |
| **cursor** | **str** | Pagination cursor from a previous response | \[optional\] |

### voice\_unbind\_number()\#

Unbind a phone number from a deployed agent

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    agent_id = 'agent_id_example'

    phone_number = 'phone_number_example'

    response = await client.voice.voice_unbind_number(agent_id, phone_number)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **agent\_id** | **str** | Agent id |  |
| **phone\_number** | **str** | E.164 phone number |  |

### voice\_update\_agent()\#

Publish changes to a deployed voice agent

```
from pingram import Pingram

async with Pingram(api_key="pingram_sk_...") as client:

    agent_id = 'agent_id_example'

    update_voice_agent_request = UpdateVoiceAgentRequest()

    response = await client.voice.voice_update_agent(agent_id, update_voice_agent_request)

    print(response)
```

#### Parameters\#

| Name | Type | Description | Notes |
| --- | --- | --- | --- |
| **agent\_id** | **str** | Agent id |  |
| **update\_voice\_agent\_request** | **UpdateVoiceAgentRequest** | See Request Body Properties below |  |

#### Request Body Properties\#

| Name | Type | Description |
| --- | --- | --- |
| `spec` | object | (required) |
| `spec.name` | string | (required) |
| `spec.instructions` | string | (required) |
| `spec.inbound` | object | (required) |
| `spec.inbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.inbound.greeting` | string | (required) |
| `spec.outbound` | object | (required) |
| `spec.outbound.firstAction` | “speak” \| “wait” | (required) |
| `spec.outbound.opener` | string | (required) |
| `spec.outbound.voicemailAction` | “hangup” \| “message” \| “continue” | (required) |
| `spec.outbound.voicemailMessage` | string |  |
| `spec.model` | object \| object | (required) Speech pipeline. Prefer s2s mode (e.g. `openai:gpt-realtime` with voice `marin`). |
| `spec.model.mode` | “chained” | (required) |
| `spec.model.llm` | string | (required) ‘provider:model’, e.g. ‘openai:gpt-4o’ |
| `spec.model.stt` | string | (required) ‘provider:model’, e.g. ‘deepgram:nova-3’ |
| `spec.model.tts` | string | (required) ‘provider:model’, e.g. ‘elevenlabs:eleven\_multilingual\_v2’ |
| `spec.model.voiceId` | string | (required) Provider-native voice id for the selected TTS provider (e.g. ElevenLabs UUID, OpenAI `alloy`). |
| `spec.model.language` | string | (required) |
| `spec.model.speechSpeed` | number | (required) |
| `spec.model.temperature` | number | (required) |
| `spec.model.maxTokens` | number | (required) |
| `spec.tools` | (object \| object \| object \| object \| object)\[\] | (required) |
| `spec.variables` | object\[\] | (required) |
| `spec.variables[].name` | string | (required) |
| `spec.variables[].description` | string |  |
| `spec.variables[].defaultValue` | string |  |
| `spec.conversation` | object | (required) |
| `spec.conversation.turnDetection` | “semantic” \| “vad” | (required) |
| `spec.conversation.minEndOfTurnSilenceMs` | number | (required) |
| `spec.conversation.allowInterruptions` | boolean | (required) |
| `spec.conversation.minInterruptionDurationMs` | number | (required) |
| `spec.conversation.silenceTimeoutSeconds` | number | (required) |
| `spec.conversation.maxCallLengthSeconds` | number | (required) |
| `spec.conversation.agentCanEndCall` | boolean | When true (default), the agent may invoke the built-in end\_call action. |
| `spec.compliance` | object | (required) |
| `spec.compliance.recordingEnabled` | boolean | (required) |
